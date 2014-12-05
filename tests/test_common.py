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
import json
import uuid
import unittest
from mock import MagicMock, patch, mock_open

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
                                "url",
                                "url"
                            ],
                            "post": [
                                "url"
                            ]
                        },
                        "scale_down": {
                            "pre": [
                                "url",
                                "url"
                            ],
                            "post": [
                                "url"
                            ]
                        }
                    }
                }
            }
        }
        """

        super(CommonTest, self).__init__(*args, **kwargs)

    def test_check_file_should_return_abs_path(self):
        with patch('os.path.isfile', return_value=True) as isfile_mock, \
                patch('os.access', return_value=True) as access_mock:
            check_file = '/config.cfg'

            self.assertEqual(common.check_file(check_file), check_file)
            isfile_mock.assert_called_once_with(check_file)
            access_mock.assert_called_once_with(check_file, os.R_OK)

    def test_check_file_should_return_none(self):
        with patch('os.path.isfile', return_value=False) as isfile_mock:
            check_file = 'config.cfg'

            self.assertIsNone(common.check_file(check_file))
            isfile_mock.assert_called_with('/etc/rax-autoscaler/config.cfg')

    def test_get_config_should_match(self):
        with patch('raxas.common.open',
                   mock_open(read_data=self._config_json), create=True) \
                as open_mock:

            self.assertEqual(common.get_config('config.cfg'),
                             json.loads(self._config_json))
            open_mock.assert_called_once_with('config.cfg')

    def test_get_config_should_return_none_with_invalid_json(self):
        with patch('raxas.common.open',
                   mock_open(read_data='trcfucbujnmk+'), create=True) \
                as open_mock:

            self.assertIsNone(common.get_config('config.cfg'))
            open_mock.assert_called_once_with('config.cfg')

    def test_get_machine_uuid(self):
        for i in xrange(0, 5):
            current_uuid = str(uuid.uuid4())
            with patch('raxas.common.subprocess') as subprocess_mock:
                subprocess_mock.Popen.return_value.communicate.\
                    return_value = ['instance-%s\n' % current_uuid]

                self.assertEqual(common.get_machine_uuid(), current_uuid)

    def test_get_user_value_from_config(self):
        with patch('sys.argv',
                   return_value=['/opt/pycharm/helpers/pycharm/noserunner.py',
                                 '/home/github/rax-autoscaler/tests/']):
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

            with self.assertRaises(KeyError):
                common.get_user_value(args, json.loads(self._config_json),
                                      'should raise KeyError')

    def test_get_group_value(self):
        self.assertEqual(common.get_group_value(json.loads(self._config_json),
                                                'group0', 'group_id'),
                         'group id')
        self.assertEqual(common.get_group_value(json.loads(self._config_json),
                                                'group0', 'scale_up_policy'),
                         'scale up policy id')
        self.assertEqual(common.get_group_value(json.loads(self._config_json),
                                                'group0', 'check_config'),
                         {})

        self.assertIsNone(
            common.get_group_value(json.loads(self._config_json),
                                   'group0', 'should raise KeyError'))

if __name__ == '__main__':
    unittest.main()
