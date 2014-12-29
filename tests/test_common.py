# -*- coding: utf-8 -*-

# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# this file is part of 'RAX-AutoScaler'
#
# Copyright 2014 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

import os
import sys
import json
import unittest
from mock import MagicMock, patch, mock_open, call

import pyrax
import pyrax.fakes
from raxas import common
from raxas.autoscale import parse_args


class CommonTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self._config_json = """
    {
        "auth": {
            "os_username": "api_username",
            "os_password": "api_key",
            "os_region_name": "os_region_name"
    },
    "autoscale_groups": {
        "group0": {
            "group_id": "group id",
            "scale_up_policy": "scale up policy id",
            "scale_down_policy": "scale down policy id",
            "webhooks": {
                "scale_up": {
                    "pre": [
                        "preup1",
                        "preup2"
                    ],
                    "post": [
                        "postup1"
                    ]
                },
                "scale_down": {
                    "pre": [
                        "predwn1",
                        "predwn2"
                    ],
                    "post": [
                        "postdwn1"
                    ]
                }
            },
            "plugins":{
                "raxmon":{
                    "scale_up_threshold": 0.6,
                    "scale_down_threshold": 0.4,
                    "check_config": {},
                    "metric_name": "1m",
                    "check_type": "agent.load_average"
                        }
                    }
                }
            }
        }
        """

        super(CommonTest, self).__init__(*args, **kwargs)

    @patch('os.path.isfile', return_value=True)
    @patch('os.access', return_value=True)
    def test_check_file_should_return_abs_path(self, access_mock, isfile_mock):
        check_file = '/config.cfg'

        self.assertEqual(common.check_file(check_file), check_file)
        isfile_mock.assert_called_once_with(check_file)
        access_mock.assert_called_once_with(check_file, os.R_OK)

    @patch('os.path.isfile', return_value=False)
    def test_check_file_should_return_none(self, isfile_mock):
        check_file = 'config.cfg'

        self.assertEqual(common.check_file(check_file), None)
        isfile_mock.assert_called_with('/etc/rax-autoscaler/config.cfg')

    def test_get_config_should_match(self):
        with patch('__builtin__.open',
                   mock_open(read_data=self._config_json)) as open_mock:

            self.assertEqual(common.get_config('config.cfg'),
                             json.loads(self._config_json))
            open_mock.assert_called_once_with('config.cfg')

    def test_get_config_should_return_none_with_invalid_json(self):
        with patch('__builtin__.open',
                   mock_open(read_data='trcfucbujnmk+')) as open_mock:

            self.assertEqual(common.get_config('config.cfg'), None)
            open_mock.assert_called_once_with('config.cfg')

    @patch('__builtin__.open')
    @patch('os.path.isfile', return_value=True)
    def test_get_machine_uuid_from_cache(self, isfile_mock, open_mock):
        open_mock = mock_open(open_mock, read_data='0a6ebf42-d4ff-'
                                                   '4075-9425-ce50dda33955\n')
        file_handle = open_mock()
        file_handle.readline.return_value = '0a6ebf42-d4ff-' \
                                            '4075-9425-ce50dda33955\n'

        self.assertEqual(common.read_uuid_cache(), '0a6ebf42-d4ff-'
                                                   '4075-9425-ce50dda33955')

    @patch('os.path.isfile', return_value=False)
    def test_get_uuid_returns_none_when_missing_cache(self, isfile_mock):
        self.assertEqual(common.read_uuid_cache(), None)

    @patch('__builtin__.open')
    @patch('os.path.isfile', return_value=True)
    def test_get_uuid_returns_none_with_empty_cache(self, isfile_mock,
                                                    open_mock):
        open_mock = mock_open(open_mock)
        file_handle = open_mock()
        file_handle.readline.return_value = ''

        self.assertEqual(common.read_uuid_cache(), None)

    @patch('__builtin__.open')
    @patch('os.path.isfile', return_value=True)
    def test_get_uuid_returns_none_with_empty_datastore(self, isfile_mock,
                                                        open_mock):
        open_mock = mock_open(open_mock, read_data='iid-datasource-none\n')
        file_handle = open_mock()
        file_handle.readline.return_value = 'iid-datasource-none\n'

        self.assertEqual(common.read_uuid_cache(), None)

    @patch('__builtin__.open')
    def test_write_uuid_cache(self, open_mock):
        open_mock = mock_open(open_mock)
        common.write_uuid_cache('0a6ebf42-d4ff-4075-9425-ce50dda33955')

        file_handle = open_mock()
        self.assertEqual(file_handle.write.call_count, 1)
        file_handle.write.assert_called_once_with('0a6ebf42-d4ff-4075-9425-'
                                                  'ce50dda33955\n')

    @patch('raxas.common.read_uuid_cache', return_value=None)
    @patch('raxas.common.write_uuid_cache')
    @patch('netifaces.interfaces')
    @patch('netifaces.ifaddresses')
    @patch('pyrax.autoscale')
    @patch('pyrax.cloudservers')
    def test_get_machine_uuid(self, cloud_servers_mock, autoscale_mock,
                              ifaddr_mock, interfaces_mock, write_uuid_mock,
                              read_uuid_mock):

        uuid = 'eb8f2464-17a4-4796-a1ba-ab635ad287b9'
        ifaddr_mock.return_value = {2: [{'addr': '119.9.94.249'}]}
        interfaces_mock.return_value = ['eth0']
        autoscale_mock.ScalingGroup.get_state.return_value = {'active': [uuid]}

        get_mock = cloud_servers_mock.servers.get.return_value
        get_mock.networks.values.return_value = \
            [['119.9.94.249', '2401:1800:7800:102:be76:4eff:fe1c:1945'],
             ['10.176.68.154']]
        get_mock.id = uuid

        self.assertEqual(common.get_machine_uuid(autoscale_mock.ScalingGroup),
                         uuid)

    def test_get_user_value_from_config(self):
        sys.argv = ['/path/to/noserunner.py']
        args = parse_args()

        self.assertEqual(
            common.get_user_value(args, json.loads(self._config_json),
                                  'os_username'), 'api_username')
        self.assertEqual(
            common.get_user_value(args, json.loads(self._config_json),
                                  'os_password'), 'api_key')
        self.assertEqual(
            common.get_user_value(args, json.loads(self._config_json),
                                  'os_region_name'), 'os_region_name')

        self.assertEqual(common.get_user_value(args,
                                               json.loads(self._config_json),
                                               'should raise KeyError'),
                         None)

    def test_get_group_value(self):
        config = json.loads(self._config_json)
        self.assertEqual(common.get_group_value(config, 'group0', 'group_id'),
                         'group id')
        self.assertEqual(common.get_group_value(config, 'group0',
                                                'scale_up_policy'),
                         'scale up policy id')

        self.assertEqual(common.get_group_value(config, 'group0',
                                                'should raise KeyError'), None)

    def test_get_webhook_value(self):
        config = json.loads(self._config_json)
        self.assertEqual(common.get_webhook_value(config, 'group0',
                                                  'scale_up'),
                         {'post': ['postup1'], 'pre': ['preup1', 'preup2']})
        self.assertEqual(common.get_webhook_value(config, 'group0',
                                                  'scale_down'),
                         {'post': ['postdwn1'], 'pre': ['predwn1', 'predwn2']})

        self.assertEqual(common.get_webhook_value(config, 'group0',
                                                  'should raise KeyError'),
                         None)

    @patch('requests.post')
    def test_webhook_call(self, post_mock):
        config = json.loads(self._config_json)
        post_mock.return_value.status_code = 200

        common.webhook_call(config, 'group0', 'scale_up', 'pre')
        self.assertEqual(post_mock.call_count, 2)

    @patch('requests.post')
    def test_webhook_should_not_send_request_on_empty_input(self,
                                                            post_mock):
        config = json.loads(self._config_json)

        common.webhook_call(config, '', '', '')
        self.assertEqual(post_mock.call_count, 0)

    @patch('requests.post')
    @patch('raxas.common.get_group_value')
    def test_webhook_should_not_call_on_invalid_group(self,
                                                      webhook_mock,
                                                      post_mock):
        config = json.loads(self._config_json)

        common.webhook_call(config, 'group does not exist', 'scale_up', 'pre')
        self.assertEqual(post_mock.call_count, 0)

    @patch('requests.post')
    def test_webhook_should_not_call_on_invalid_policy(self,
                                                       post_mock):
        config = json.loads(self._config_json)

        common.webhook_call(config, 'group0', 'policy does not exist', 'pre')
        self.assertEqual(post_mock.call_count, 0)

    @patch('requests.post')
    def test_webhook_should_not_call_on_invalid_config(self,
                                                       post_mock):
        config = json.loads("""
            {
                "autoscale_groups": {
                    "group0": {
                        "webhooks": {
                            "scale_up": {
                                "pre": [
                                    "preup1",
                                    "preup2"
                                ],
                                "post": [
                                    "postup1"
                                ]
                            }
                        }
                    }
                }
            }
            """)

        common.webhook_call(config, 'group0', 'scale_up', 'pre')
        self.assertEqual(post_mock.call_count, 0)

    @patch('requests.post')
    def test_webhook_should_not_call_on_invalid_key(self,
                                                    post_mock):
        config = json.loads(self._config_json)

        common.webhook_call(config, 'group0', 'scale_up', 'does not exist')
        self.assertEqual(post_mock.call_count, 0)

    def test_is_ipv4(self):
        self.assertEqual(common.is_ipv4('127.0.0.1'), True)
        self.assertEqual(common.is_ipv4('1.2.3.4'), True)
        self.assertEqual(common.is_ipv4('100.200.230.1'), True)
        self.assertEqual(common.is_ipv4('::1'), False)
        self.assertEqual(common.is_ipv4('100.200.300.400'), False)
        self.assertEqual(common.is_ipv4('hello'), False)
        self.assertEqual(common.is_ipv4('1.2.3.4.5'), False)

    def test_get_scaling_group_servers_returns_none_on_invalid_group(self):
        config = json.loads(self._config_json)

        self.assertEqual(common.get_scaling_group('invalid-group', config), None)

    def test_get_scaling_group_servers_returns_none_on_error(self):
        config = json.loads(self._config_json)

        self.assertEqual(common.get_scaling_group('group0', config), None)