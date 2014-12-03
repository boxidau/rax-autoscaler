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
import logging


def get_logger():
    """This function instantiate the logger.

    :return: logger

    """
    logger = logging.getLogger(__name__)
    return logger


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
    logger = get_logger()
    logger.info("Loading config file: '%s'" % config_file)
    try:
        json_data = open(config_file)
        data = json.load(json_data)
        return data
    except Exception, e:
        logger.error("Error: " + str(e))

    return None


def get_machine_uuid():
    """This function uses subprocess to get node uuid

      :returns: machine uuid

    """
    logger = get_logger()
    try:
        name = subprocess.Popen(['xenstore-read name'], shell=True,
                                stdout=subprocess.PIPE).communicate()[0]
        id = name.strip()
        return id[9:]
    except Exception, e:
        logger.error("Error: " + str(e))

    return None


def get_user_value(args, config, key):
    """This function returns value associated with the key if its available in
       user arguments else in json config file.

      :param args: user arguments
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    logger = get_logger()
    value = None
    if args[key] is None:
        try:
            value = config['auth'][key.lower()]
        except:
            logger.error("Invalid config, '" + key +
                         "' key not found in authentication section")
    else:
        value = args[key]

    return value


def get_group_value(config, group, key):
    """This function returns value in autoscale_groups section associated with
       provided key.

    :type config: object
      :param group: group name
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    logger = get_logger()
    try:
        value = config['autoscale_groups'][group][key]
        if value is not None:
            return value
    except:
        logger.error("Error: unable to get value for key '" + key +
                     "' from group '" + group + "'")

    return None


def get_webhook_value(config, group, key):
    """This function returns value in webhooks section of json file which is
       associated with provided key.

      :param group: group name
      :param config: json configuration data
      :param key: key name
      :returns: value associated with key

    """
    logger = get_logger()
    try:
        value = config['autoscale_groups'][group]['webhooks'][key]
        if value is not None:
            return value
    except:
        logger.warning("Unable to find value for key: '%s' in group '%s'"
                       % (key, group))

    return None


def webhook_call(config_data, group, policy, key):
    """This function makes webhook calls.

      :param config_data: json configuration data
      :param group: group name
      :param policy: policy type
      :param key: key name

    """
    logger = get_logger()

    logger.info('Launching %s webhook call' % key)
    url_list = get_webhook_value(config_data, group, policy)
    if url_list is None:
        return None

    group_id = get_group_value(config_data, group, 'group_id')
    if group_id is None:
        return None

    up_policy_id = get_group_value(config_data, group,
                                   'scale_up_policy')
    if up_policy_id is None:
        return None

    down_policy_id = get_group_value(config_data, group,
                                     'scale_down_policy')
    if down_policy_id is None:
        return None

    check_type = get_group_value(config_data, group, 'check_type')
    if check_type is None:
        return None

    metric_name = get_group_value(config_data, group,
                                  'metric_name')
    if check_type is None:
        return None

    up_threshold = get_group_value(config_data, group,
                                   'scale_up_threshold')
    if up_threshold is None:
        return None

    down_threshold = get_group_value(config_data, group,
                                     'scale_down_threshold')
    if up_threshold is None:
        return None

    data = json.dumps({'group_id': group_id,
                       'scale_up_policy': up_policy_id,
                       'scale_down_policy': down_policy_id,
                       'check_type': check_type,
                       'metric_name': metric_name,
                       'scale_up_threshold': up_threshold,
                       'scale_down_threshold': down_threshold})

    urls = url_list[key]
    for url in urls:
        logger.info("Sending POST request to url: '%s'" % url)
        try:
            req = urllib2.Request(url, data,
                                  {'Content-Type': 'application/json'})
            f = urllib2.urlopen(req)
            response = f.read()
            f.close()
        except Exception, e:
            logger.warning(str(e))

    return None
