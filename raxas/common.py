# Encoding: utf-8
#
# rax-autoscaler
#
# Copyright 2014, Rackspace, US Inc.
#
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
#

from __future__ import print_function
import os
import pyrax
import sys
import pyrax.exceptions as pexc
from termcolor import colored
import ConfigParser
import subprocess
import datetime
import json


def check_file(fname):
    file_abspath = os.path.abspath(fname)
    if os.path.isfile(file_abspath) and os.access(file_abspath, os.R_OK):
        return file_abspath
    else:
        preDefinedPath = '/etc/rax-autoscaler/'+fname
        # Check in /etc/rax-autoscaler/config path
        if os.path.isfile(preDefinedPath):
            if os.access(preDefinedPath, os.R_OK):
                return preDefinedPath
    # Either file is missing or is not readable
    return


def log(level, message):
    if level == 'OK':
        print(colored('[  OK  ]', 'green'), "\t", message, file=sys.stderr)
    elif level == 'INFO':
        print(colored('[ INFO ]', 'blue'), "\t", message, file=sys.stderr)
    elif level == 'ERROR':
        print(colored('[ FAIL ]', 'red'), "\t", message, file=sys.stderr)
    else:
        print(message)


def get_config(config_file):
    try:
        json_data = open(config_file)
        data = json.load(json_data)
        return data
    except:
        return


def get_machine_uuid():
    name = subprocess.Popen(['xenstore-read name'], shell=True,
                            stdout=subprocess.PIPE).communicate()[0]
    id = name.strip()
    return id[9:]


def get_user_value(args, config, key):
    if args[key] is None:
        try:
            value = config['AUTH'][key.upper()]
            if not value:
                return
        except:
            raise Exception("Invalid config, '" + key +
                            "' key not found in authentication section")
            return
    else:
        value = args[key]
    return value


def get_group_value(config, group, key):
    try:
        value = config['AUTOSCALE_GROUPS'][group][key]
        if not value:
            return
        return value
    except:
        return


def get_webhook_value(config, group, key):
    try:
        value = config['AUTOSCALE_GROUPS'][group]['WEBHOOKS'][key]
        if not value:
            return
        return value
    except:
        return
