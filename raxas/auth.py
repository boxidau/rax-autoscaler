# -*- coding: utf-8 -*-

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

import json
import logging
import os.path
import pprint
import pyrax
import traceback


class Auth(object):
    '''
    class which implements Rackspace Authentication
    '''

    def __init__(self, username, apikey, region,
                 identity_type="rackspace",
                 token_filename=os.path.expanduser('~/.rax-autoscaler-token')):
        logger = logging.getLogger(__name__)
        self._username = username
        self._apikey = apikey
        self._identity_type = identity_type
        self._region = region
        self._token_filename = token_filename
        self._token = None
        self._tenant_id = None
        logger.debug(self.__str__())

    def __str__(self, *args, **kwargs):
        return ("username: %s, apikey: %s, identity_type: %s, "
                "region: %s, token_filename: %s, token: %s, "
                "tenant_id: %s" %
                (self._username, self._apikey, self._identity_type,
                 self._region, self._token_filename, self._token,
                 self._tenant_id))

    def status(self):
        '''
        similar to __str__, but queries pyrax for values
        '''
        pi = pyrax.identity
        return ("pyrax reports -- "
                "username: %s, apikey: %s, region: %s, token: %s, "
                "tenant_id: %s" %
                (pi.username, pi.api_key, pi.region, pi.token, pi.tenant_id))

    @property
    def token_filename(self):
        return self._token_filename

    def authenticate(self):
        '''
        authentication facility, tries to load a token from file,
        authenticate with it, and if it fails then tries to authenticate
         with credentials
        '''
        logger = logging.getLogger(__name__)
        # try to authenticate with token
        if self.load_token():
            logger.debug("loaded token '%s' from file '%s'" %
                         (pprint.pformat(self._token), self._token_filename))
            if self.authenticate_token():
                logger.info('authenticated successfully')
                logger.debug("authenticated with token '%s' from file '%s'" %
                             (self._token, self._token_filename))
                return True
            else:
                logger.debug("cannot authenticate with token '%s' "
                             "from file '%s'"
                             % (self._token, self._token_filename))
        # try to authenticate with credentials
        if self.authenticate_credentials():
            logger.info('authenticated successfully')
            logger.debug("authenticated with credentials, username:%s,"
                         "api-key:%s, region:%s, identity_type:%s" %
                         (self._username, self._apikey, self._region,
                          self._identity_type))
            return True
        else:
            logger.debug("cannot authenticate with credentials, username:%s, "
                         "api-key:%s, region:%s, identity_type:%s" %
                         (self._username, self._apikey, self._region,
                          self._identity_type))
            return False

    def authenticate_credentials(self):
        '''
        authenticate with username and api-key

        @identity_type    'rackspace', 'openstack'
        @username
        @apikey
        @region            LON,SYD,DFW, etc
        '''
        logger = logging.getLogger(__name__)
        logger.debug('authenticating with credentials '
                     '(identity_type:%s, username:%s, api-key:%s, region=%s)'
                     % (self._identity_type, self._username, self._apikey,
                        self._region))
        try:
            pyrax.set_setting("identity_type", self._identity_type)
            pyrax.set_credentials(self._username, self._apikey,
                                  region=self._region)
            logger.info("authenticated with credentials, username:%s, "
                        "api-key:%s, region:%s, identity_type:%s" %
                        (self._username, self._apikey, self._region,
                         self._identity_type))
            logger.debug("user authenticated: %s"
                         % pyrax.identity.authenticated)
            if pyrax.identity.authenticated:
                self._token = pyrax.identity.auth_token
                self._tenant_id = pyrax.identity.tenant_id
                self.save_token()
            return pyrax.identity.authenticated
        except pyrax.exceptions.AuthenticationFailed:
            logger.warn("cannot authenticate with credentials")
            return False

    def authenticate_token(self):
        '''
        authenticate with Rackspace Cloud
        using existing token
        tenant_id: see top-right --> tenant_id (#XXX)
        '''
        logger = logging.getLogger(__name__)
        pyrax.set_setting('identity_type', self._identity_type)
        try:
            pyrax.auth_with_token(self._token, self._tenant_id)
            logging.info('authenticated with token:%s, tenant_id:%s' %
                         (self._token, self._tenant_id))
            return True
        except:
            logging.info('cannot authenticate with token:%s, tenant_id:%s' %
                         (self._token, self._tenant_id))
            logger.debug(traceback.format_exc())
            return False

    def force_unauthenticate(self):
        '''
        Force logout, i.e. unauthenticate and delete token file
        '''
        # unauthenticate
        try:
            pyrax.identity.unauthenticate()
        except AttributeError:
            pass
        # delete token file
        try:
            os.unlink(self._token_filename)
        except OSError:
            pass

    def load_token(self):
        '''
        load token from file

        Actually it loads 'token' and 'tenant_id' from token file.
        '''
        logger = logging.getLogger(__name__)
        try:
            with open(self._token_filename, 'r') as f:
                data = json.load(f)
            logger.debug("loaded data '%s' from file '%s'" %
                         (pprint.pformat(data), self._token_filename))
        except ValueError:
            logger.error("cannot decode JSON data in token file'%s'" %
                         self._token_filename)
            logger.debug(traceback.format_exc())
            return False
        except:
            logger.error("cannot read token data from file '%s'" %
                         self._token_filename)
            logger.debug(traceback.format_exc())
            return False
        try:
            self._token = data['token']
            self._tenant_id = data['tenant_id']
            return True
        except KeyError:
            logger.error()
            logger.debug(traceback.format_exc())
            return False

    def save_token(self):
        '''
        save token to file
        '''
        logger = logging.getLogger(__name__)
        data = {'token': self._token, 'tenant_id': self._tenant_id}
        try:
            with open(self._token_filename, 'w') as f:
                json.dump(data, f)
            return True
        except:
            logger.error("cannot write data '%s' to file '%s'" %
                         (pprint.pformat(data), self._token_filename))
            logger.debug(traceback.format_exc())
            return False
