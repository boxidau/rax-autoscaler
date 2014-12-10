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
import uuid
import unittest
from mock import MagicMock, patch, mock_open, call

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
                    "check_type": "agent.load_average",
                    "check_config": {},
                    "metric_name": "1m",
                    "scale_up_threshold": 0.6,
                    "scale_down_threshold": 0.4,
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

    @patch('raxas.common.subprocess')
    def test_get_machine_uuid(self, subprocess_mock):
        for i in xrange(0, 5):
            current_uuid = str(uuid.uuid4())
            subprocess_mock.Popen.return_value.communicate.\
                return_value = ['instance-%s\n' % current_uuid]

            self.assertEqual(common.get_machine_uuid(), current_uuid)

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

    def test_get_user_value_from_args(self):
        sys.argv = ['/path/to/noserunner.py', '--os-username', 'test.user']
        args = parse_args()

        self.assertEqual(
            common.get_user_value(args, json.loads(self._config_json),
                                  'os_username'), 'test.user')

    def test_get_group_value(self):
        config = json.loads(self._config_json)
        self.assertEqual(common.get_group_value(config, 'group0', 'group_id'),
                         'group id')
        self.assertEqual(common.get_group_value(config, 'group0',
                                                'scale_up_policy'),
                         'scale up policy id')
        self.assertEqual(common.get_group_value(config, 'group0',
                                                'check_config'), {})

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
