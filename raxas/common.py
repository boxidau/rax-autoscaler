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
import json
import requests
import logging
from uuid import UUID
import netifaces


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
        predefined_path = '/etc/rax-autoscaler/'+fname
        # Check in /etc/rax-autoscaler/config path
        if os.path.isfile(predefined_path):
            if os.access(predefined_path, os.R_OK):
                return predefined_path
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
    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def read_uuid_cache():
    logger = get_logger()

    # we're storing files in /dev/shm/ to ensure the cache is deleted on reboot
    uuid_files = ['/dev/shm/.raxas-uuid.cache',
                  # instance-id is populated with the uuid if the server was
                  # spun up with config_drive set to True
                  '/var/lib/cloud/data/instance-id']

    if sys.platform in ['win32', 'cygwin']:
        # Windows doesn't have a built in equivalent to /dev/shm so we'll
        # disable file caching for now to ensure we don't have a stale cache
        # if an image is taken of the servers running in the autoscale group
        logger.info('no uuid caching for windows, moving on...')
        return None

    for file_path in uuid_files:
        if not os.path.isfile(file_path):
            continue

        with open(file_path, 'r') as cache_file:
            line = cache_file.readline().strip()
            if line == 'iid-datasource-none':
                # This happens if the server was spun up without config_drive
                # set to True
                logger.info('cloud-init datastore does not contain uuid')
                continue

            try:
                # I'm creating a UUID object from the contents of the cache
                # to verify it's a valid UUID. ValueError is thrown if invalid
                uuid = UUID(line)
                return str(uuid)
            except ValueError:
                logger.info('invalid uuid found in %s : %s'
                            % (file_path, line))
                continue

    return None


def write_uuid_cache(uuid):
    logger = get_logger()

    try:
        with open('/dev/shm/.raxas-uuid.cache', 'w+') as cache_file:
            logger.info('updating uuid cache /dev/shm/.raxas-uuid.cache')
            cache_file.write('%s\n' % uuid)
    except IOError as error:
        logger.error('unable to write uuid cache file:%s' % error.args)


def get_machine_uuid(scaling_group):
    """This function will search for the server's UUID and return it.

    First it searches in a rax-autoscaler cache, followed by cloud-init cache.
    If it cannot find a cached UUID, it will get the details of each server in
    the scaling group in turn and attempt to match the local IP address with
    that of the server object returned from the API

    :param scaling_group: The pyrax scaling group of the current group we
                          are processing
    :return: None if no UUID could be matched against a cache file or the API.
             UUID as a string
    """
    logger = get_logger()

    uuid = read_uuid_cache()
    if uuid is not None:
        logger.info('found server UUID from cache: %s' % uuid)
        return uuid

    # if we didn't get anything from any cache files, we'll loop through the
    # servers in the scaling group, get the server details and cross check the
    # ip addresses against what's on *this* server

    local_ips = []
    for interface in netifaces.interfaces():
        try:
            for ip in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                if ip['addr'] != '127.0.0.1':
                    local_ips.append(ip['addr'])
        except KeyError:
            continue

    active_servers = scaling_group.get_state()['active']
    servers_api = pyrax.cloudservers
    for active_uuid in active_servers:
        server = servers_api.servers.get(active_uuid)

        server_ips = [ip for network in server.networks.values()
                      for ip in network]
        matching_ips = set(server_ips).intersection(local_ips)
        if len(matching_ips) > 0:
            logger.info('found uuid from matching ip address: %s' % server.id)
            write_uuid_cache(server.id)
            return server.id

    # only reached if we couldn't read from the cache file and couldn't find
    # this server's ip address in the scaling group's active server list
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
    try:
        if args[key] is None:
            value = config['auth'][key.lower()]
        else:
            value = args[key]
    except:
            logger.error("Invalid config, '" + key +
                         "' key not found in authentication section")

    return value


def get_group_value(config, group, key):
    """This function returns value in autoscale_groups section associated with
       provided key.

      :type config: dict
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
    try:
        urls = get_webhook_value(config_data, group, policy)[key]
    except (KeyError, TypeError):
        logger.error('Webhook urls for %s cannot be found in config' % key)
        return None

    try:
        group_config = config_data['autoscale_groups'][group]
        plugin_config = get_plugin_config(config_data, group, 'raxmon')
        data = json.dumps({
            'group_id': group_config['group_id'],
            'scale_up_policy': group_config['scale_up_policy'],
            'scale_down_policy': group_config['scale_down_policy'],
            'check_type': plugin_config['check_type'],
            'metric_name': plugin_config['metric_name'],
            'scale_up_threshold': plugin_config['scale_up_threshold'],
            'scale_down_threshold': plugin_config['scale_down_threshold']
        })
    except KeyError as error:
        logger.error('Cannot build webhook data. invalid key: %s' % error)
        return None

    for url in urls:
        logger.info("Sending POST request to url: '%s'" % url)
        try:
            response = requests.post(url, json=data)
            logger.info("Received status code %d from url: '%s'"
                        % (response.status_code, url))
        except Exception as e:
            logger.warning(str(e))

    return None


def exit_with_error(msg):
    """This function prints error message and exit with error.

    :param msg: error message
    :returns: 1 (int) -- the return code

    """
    logger = get_logger()

    if msg is None:
        try:
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: %s' % log_file)
        except:
            print('(info) rax-autoscale completed with an error')
    else:
        try:
            logger.error(msg)
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: %s' % log_file)
        except:
            print('(error) %s' % msg)
            print('(info) rax-autoscale completed with an error')

    exit(1)


def get_server(server_id):
    """ It gets Cloud server object by server_id

    """
    cs = pyrax.cloudservers
    try:
        return filter(lambda s: s.id == server_id, [s for s in cs.list()])[0]
    except:
        logging.info('no cloud server with id: %s' % server_id)
        return None


def scaling_group_servers(sgid):
    """ list servers' id in scaling group sgid

    :param sgid: scaling group id

    """
    logger = get_logger()
    a = pyrax.autoscale
    try:
        sg = a.get(sgid)
        return sg
    except:
        logger.error('Unable to find scaling group with id:%s' % sgid)
        return


def get_plugin_config(config, group, plugin):
        """This function returns the plugin section associated with a autoscale_group

          :type config: dict
          :param group: group name
          :param plugin: plugin name
          :param config: json configuration data
          :returns: value associated with key

        """
        logger = get_logger()
        try:
            value = config['autoscale_groups'][group]['plugins'][plugin]
            if value is not None:
                return value
        except KeyError:
            logger.error("Error: unable to get plugin values for '" + plugin +
                         "' from group '" + group + "'")

        return None


def get_scaling_group(group, config_data):
    """This function checks and gets active servers in scaling group

    :param group: group name
    :param config_data: json configuration data
    :returns: scalingGroup if server state is active else null

    """

    logger = get_logger()

    group_id = get_group_value(config_data, group, 'group_id')
    if group_id is None:
        logger.error('Unable to get group_id from json file')
        return

    scalingGroup = scaling_group_servers(group_id)
    if scalingGroup is None:
        return
    # Check active server(s) in scaling group
    if len(scalingGroup.get_state()['active']) == 0:
        logger.warning('Unable to find any active server in scaling group')
        return
    else:
        logger.info('Server(s) in scaling group: %s' %
                    ', '.join(['(, %s)'
                               % s_id
                               for s_id in
                               scalingGroup.get_state()['active']]))
    logger.info('Current Active Servers: ' +
                str(scalingGroup.get_state()['active_capacity']))
    return scalingGroup


def is_ipv4(address):
    """It checks if address is valid IP v4

    """
    import socket
    try:
        socket.inet_aton(address)
        return True
    except socket.error:
        return False
