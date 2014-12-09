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
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from mock import patch, mock_open
import pyrax
from raxas.auth import Auth


class AuthTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(AuthTest, self).__init__(*args, **kwargs)
        self.username = "AUTHUSER"
        self.password = "AUTHPASS"
        self.token = "testtokenplsignore"
        self.region = "HKG"
        self.token_file_contents = """{"tenant_id": 123456,
        "token": "testtokenplsignore"}"""
        self.empty_json = """{"test":""}"""
        self.tenantid = "123456"
        self.token = "testtokenplsignore"

    def test_load_token_true(self):
        auth = Auth(self.username, self.token, self.region)
        with patch('__builtin__.open',
                   mock_open(read_data=self.token_file_contents), create=True):
            self.assertTrue(auth.load_token())

    def test_load_token_nofile(self):
        auth = Auth(self.username, self.token, self.region)
        with patch('__builtin__.open', mock_open()):
            self.assertFalse(auth.load_token())

    def test_load_token_ioerror(self):
        auth = Auth(self.username, self.token, self.region)
        with patch('__builtin__.open', mock_open(
                read_data=self.token_file_contents)) as mocked_open:
            mocked_open.side_effect = IOError()
            self.assertFalse(auth.load_token())

    def test_load_token_wrong_keys(self):
        auth = Auth(self.username, self.token, self.region)
        with patch('__builtin__.open', mock_open(read_data=self.empty_json),
                   create=True):
            self.assertFalse(auth.load_token())

    def test_save_token(self):
        auth = Auth(self.username, self.token, self.region)
        auth._tenant_id = self.tenantid
        auth._token = self.token
        auth._token_filename = "token.file"
        with patch('__builtin__.open', mock_open(), create=True) as mocked:
            self.assertTrue(auth.save_token())
            mocked.assert_called_once_with('token.file', 'w')

    def test_authenticate_token_success(self):
        auth = Auth(self.username, self.token, self.region)
        auth._tenant_id = self.tenantid
        auth._token = self.token
        auth._token_filename = "token.file"
        with patch('pyrax.auth_with_token', return_value=True):
            self.assertTrue(auth.authenticate_token())

    def test_authenticate_token_fail(self):
        auth = Auth(self.username, self.token, self.region)
        auth._tenant_id = self.tenantid
        auth._token = self.token
        auth._token_filename = "token.file"
        with patch('pyrax.auth_with_token', return_value=True) as mocked:
            mocked.side_effect = Exception
            self.assertFalse(auth.authenticate_token())

    @patch('pyrax.identity', create=True)
    @patch('pyrax.set_credentials', return_value=True, create=True)
    def test_authenticate_creds_success(self, mock_creds, mock_auth):
        auth = Auth(self.username, self.token, self.region)

        self.assertTrue(auth.authenticate_credentials())

    @patch('pyrax.identity', create=True)
    @patch('pyrax.set_credentials', return_value=True, create=True)
    def test_authenticate_creds_false(self, mock_creds, mock_auth):
        auth = Auth(self.username, self.token, self.region)
        mock_creds.side_effect = pyrax.exceptions.AuthenticationFailed

        self.assertFalse(auth.authenticate_credentials())


if __name__ == "__main__":
    unittest.main()
