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
import urllib2


def check_file(fname):
    """This function checks if file exists and is readable.

      :param fname: file name
      :returns: file name with absolute path

    """
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


def get_config(config_file):
    """This function read and returns jsons configuration data

      :param config_file: json configuration file name
      :returns: json data

    """
    try:
        json_data = open(config_file)
        data = json.load(json_data)
        return data
    except:
        return


def get_machine_uuid():
    """This function uses subprocess to get node uuid

      :returns: machine uuid

    """
    name = subprocess.Popen(['xenstore-read name'], shell=True,
                            stdout=subprocess.PIPE).communicate()[0]
    id = name.strip()
    return id[9:]


def get_user_value(args, config, key):
    """This function returns value associated with the key if its available in
       user arguments else in json config file.

      :param args: user arguments
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    if args[key] is None:
        try:
            value = config['auth'][key.lower()]
            if value is None:
                return
        except:
            raise Exception("Invalid config, '" + key +
                            "' key not found in authentication section")
            return
    else:
        value = args[key]
    return value


def get_group_value(config, group, key):
    """This function returns value in autoscale_groups section associated with
       provided key.

      :param group: group name
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    try:
        value = config['autoscale_groups'][group][key]
        if value is None:
            return
        return value
    except:
        return


def get_webhook_value(config, group, key):
    """This function returns value in webhooks section of json file which is
       associated with provided key.

      :param group: group name
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    try:
        value = config['autoscale_groups'][group]['webhooks'][key]
        if value is None:
            return
        return value
    except:
        return


def webhook_call(config_data, group, policy, key):
    """This function makes webhook calls.

      :param config_data: json configuration data
      :param group: group name
      :param policy: policy type
      :param key: key name
      :returns: 1 (int) -- return value

    """

    url_list = get_webhook_value(config_data, group, policy)
    if url_list is None:
        logger.error('Unable to get webhook urls from json file')
        return

    group_id = get_group_value(config_data, group, 'group_id')
    if group_id is None:
        logger.error('Unable to get group_id from json file')
        return

    up_policy_id = get_group_value(config_data, group,
                                   'scale_up_policy')
    if up_policy_id is None:
        logger.error('Unable to get scale_up_policy from json file')
        return

    down_policy_id = get_group_value(config_data, group,
                                     'scale_down_policy')
    if down_policy_id is None:
        logger.error('Unable to get scale_down_policy from json file')
        return

    check_type = get_group_value(config_data, group, 'check_type')
    if check_type is None:
        logger.error('Unable to get check_type from json file')
        return

    metric_name = get_group_value(config_data, group,
                                  'metric_name')
    if check_type is None:
        logger.error('Unable to get metric_name from json file')
        return

    up_threshold = get_group_value(config_data, group,
                                   'scale_up_threshold')
    if up_threshold is None:
        logger.error('Unable to get scale_up_threshold from json file')
        return

    down_threshold = get_group_value(config_data, group,
                                     'scale_down_threshold')
    if up_threshold is None:
        logger.error('Unable to get scale_down_threshold from json file')
        return

    data = json.dumps({'group_id': group_id,
                       'scale_up_policy': up_policy_id,
                       'scale_down_policy': down_policy_id,
                       'check_type': check_type,
                       'metric_name': metric_name,
                       'scale_up_threshold': up_threshold,
                       'scale_down_threshold': down_threshold})

    urls = url_list[key]

    for url in urls:
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()

    return 1
