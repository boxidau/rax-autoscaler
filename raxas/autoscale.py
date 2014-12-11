#!/usr/bin/env python
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

import common
import pyrax
import argparse
import time
import os
import sys
import logging.config
import random
from colouredconsolehandler import ColouredConsoleHandler
from auth import Auth
import cloudmonitor
import subprocess
from version import return_version


# CHECK logging.conf
logging_config = common.check_file('logging.conf')

if logging_config is None:
    logging.handlers.ColouredConsoleHandler = ColouredConsoleHandler
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

else:

    logging_conf_file = logging_config
    logging.handlers.ColouredConsoleHandler = ColouredConsoleHandler
    logging.config.fileConfig(logging_conf_file)
    logger = logging.getLogger(__name__)


def exit_with_error(msg):
    """This function prints error message and exit with error.

    :param msg: error message
    :type name: str
    :returns: 1 (int) -- the return code

    """
    if msg is None:
        try:
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: %s' % log_file)
        except:
            print ('(info) rax-autoscale completed with an error')
    else:
        try:
            logger.error(msg)
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: %s' % log_file)
        except:
            print ('(error) %s' % msg)
            print ('(info) rax-autoscale completed with an error')

    exit(1)


def is_node_master(scalingGroup):
    """This function checks scaling group state and determines if node is a master.

    :param scalingGroup: data about servers in scaling group retrieve from
                         cloudmonitor
    :returns: 1     : if cluster state is unknown
              2     : node is a master
              None  : node is not a master

    """
    masters = []
    node_id = common.get_machine_uuid()

    if node_id is None:
        logger.error('Failed to get server uuid')
        return 1

    sg_state = scalingGroup.get_state()
    if len(sg_state['active']) == 1:
        masters.append(sg_state['active'][0])
    elif len(sg_state['active']) > 1:
        masters.append(sg_state['active'][0])
        masters.append(sg_state['active'][1])
    else:
        logger.error('Unknown cluster state')
        return 1

    if node_id in masters:
        logger.info('Node is a master, continuing')
        return 2
    else:
        logger.info('Node is not a master, nothing to do. Exiting')
        return


def get_scaling_group(group, config_data):
    """This function checks and gets active servers in scaling group

    :param group: group name
    :param config_data: json configuration data
    :returns: scalingGroup if server state is active else null

    """
    group_id = common.get_group_value(config_data, group, 'group_id')
    if group_id is None:
        logger.error('Unable to get group_id from json file')
        return

    scalingGroup = cloudmonitor.scaling_group_servers(group_id)
    if scalingGroup is None:
        return
    # Check active server(s) in scaling group
    if len(scalingGroup.get_state()['active']) == 0:
        return
    else:
        logger.info('Server(s) in scaling group: %s' %
                    ', '.join(['(%s, %s)'
                              % (cloudmonitor.get_server_name(s_id), s_id)
                              for s_id in scalingGroup.get_state()['active']]))
    logger.info('Current Active Servers: ' +
                str(scalingGroup.get_state()['active_capacity']))
    return scalingGroup


def autoscale(group, config_data, args):
    """This function executes scale up or scale down policy

    :param group: group name
    :param config_data: json configuration data
    :param args: user provided arguments

    """
    au = pyrax.autoscale

    scalingGroup = get_scaling_group(group, config_data)
    if scalingGroup is None:
        return 1
    check_type = common.get_group_value(config_data, group, 'check_type')
    if check_type is None:
        return 1
    check_config = common.get_group_value(config_data, group, 'check_config')
    if check_config is None:
        return 1

    for s_id in scalingGroup.get_state()['active']:
        rv = cloudmonitor.add_cm_check(s_id, check_type, check_config)

    logger.info('Cluster Mode Enabled: %s' % str(args['cluster']))

    if args['cluster']:
        rv = is_node_master(scalingGroup)
        if rv is None:
            # Not a master, no need to proceed further
            return
        if rv == 1:
            # Cluster state unknown return error.
            return 1

    # Gather cluster statistics
    check_type = common.get_group_value(config_data, group, 'check_type')
    if check_type is None:
        check_type = 'agent.load_average'

    metric_name = common.get_group_value(config_data, group, 'metric_name')
    if metric_name is None:
        metric_name = '1m'

    logger.info('Gathering Monitoring Data')

    results = []
    cm = pyrax.cloud_monitoring
    # Get all CloudMonitoring entities on the account
    entities = cm.list_entities()

    # Shuffle entities so the sample uses different servers
    entities = random.sample(entities, len(entities))

    for ent in entities:
        # Check if the entity is also in the scaling group
        if ent.agent_id in scalingGroup.get_state()['active']:
            ent_checks = ent.list_checks()
            # Loop through checks to find checks of the correct type
            for check in ent_checks:
                if check.type == check_type:
                    data = check.get_metric_data_points(metric_name,
                                                        int(time.time())-300,
                                                        int(time.time()),
                                                        points=2)
                    if len(data) > 0:
                        point = len(data)-1
                        logger.info('Found metric for: ' + ent.name +
                                    ', value: ' + str(data[point]['average']))
                        results.append(float(data[point]['average']))
                        break

        # Restrict number of data points to save on API calls
        if len(results) >= args['max_sample']:
            logger.info('--max-sample value of ' + str(args['max_sample']) +
                        ' reached, not gathering any more statistics')
            break

    if len(results) == 0:
        logger.error('No data available')
        return 1
    else:
        average = sum(results)/len(results)
        scale_up_threshold = common.get_group_value(config_data, group,
                                                    'scale_up_threshold')
        if scale_up_threshold is None:
            scale_up_threshold = 0.6

    scale_down_threshold = common.get_group_value(config_data, group,
                                                  'scale_down_threshold')
    if scale_down_threshold is None:
        scale_down_threshold = 0.4

    logger.info('Cluster average for ' + check_type +
                '(' + metric_name + ') at: ' + str(average))

    if average > scale_up_threshold:
        try:
            logger.info('Above Threshold - Scaling Up')
            scale_policy_id = common.get_group_value(config_data, group,
                                                     'scale_up_policy')
            scale_policy = scalingGroup.get_policy(scale_policy_id)
            if not args['dry_run']:
                common.webhook_call(config_data, group, 'scale_up', 'pre')
                scale_policy.execute()
                common.webhook_call(config_data, group, 'scale_up', 'post')
            else:
                logger.info('Scale up prevented by --dry-run')
                logger.info('Scale up policy executed ('
                            + scale_policy_id + ')')
        except Exception, e:
            logger.warning('Scale up: %s' % str(e))
    elif average < scale_down_threshold:
        try:
            logger.info('Below Threshold - Scaling Down')
            scale_policy_id = common.get_group_value(config_data, group,
                                                     'scale_down_policy')
            scale_policy = scalingGroup.get_policy(scale_policy_id)
            if not args['dry_run']:
                common.webhook_call(config_data, group, 'scale_down', 'pre')
                scale_policy.execute()
                common.webhook_call(config_data, group, 'scale_down', 'post')
            else:
                logger.info('Scale down prevented by --dry-run')
                logger.info('Scale down policy executed (' +
                            scale_policy_id + ')')

        except Exception, e:
            logger.warning('Scale down: %s' % str(e))

    else:
        logger.info('Cluster within target paramters')


def main():
    """This function validates user arguments and data in configuration file.
       It calls auth class for authentication and autoscale to execute scaling
       policy

    """

    parser = argparse.ArgumentParser()

    parser.add_argument('--as-group', required=False,
                        help='The autoscale group config ID')
    parser.add_argument('--os-username', required=False,
                        help='Rackspace Cloud user name')
    parser.add_argument('--os-password', required=False,
                        help='Rackspace Cloud account API key')
    parser.add_argument('--config-file', required=False, default='config.json',
                        help='The autoscale configuration .ini file'
                        '(default: config.json)'),
    parser.add_argument('--os-region-name', required=False,
                        help='The region to build the servers',
                        choices=['SYD', 'HKG', 'DFW', 'ORD', 'IAD', 'LON'])
    parser.add_argument('--cluster', required=False,
                        default=False, action='store_true')
    parser.add_argument('--version', action='version',
                        help='Show version number', version=return_version())
    parser.add_argument('--dry-run', required=False, default=False,
                        action='store_true',
                        help='Do not actually perform any scaling operations '
                        'or call webhooks')
    parser.add_argument('--max-sample', required=False, default=10, type=int,
                        help='Maximum number of servers to obtain monitoring '
                        'samples from')

    args = vars(parser.parse_args())

    # CONFIG.ini
    config_file = common.check_file(args['config_file'])
    if config_file is None:
        exit_with_error("Either file is missing or is not readable: '%s'"
                        % args['config_file'])

    # Show Version
    logger.info(return_version())

    for arg in args:
        logger.debug('argument provided by user ' + arg + ' : ' +
                     str(args[arg]))

    # Get data from config.json
    config_data = common.get_config(config_file)
    if config_data is None:
        exit_with_error('Failed to read config file: ' + config_file)

    # Get group
    if not args['as_group']:
        if len(config_data['autoscale_groups'].keys()) == 1:
            as_group = config_data['autoscale_groups'].keys()[0]
        else:
            logger.debug("Getting system hostname")
            try:
                sysout = subprocess.Popen(['hostname'], stdout=subprocess.PIPE)
                hostname = (sysout.communicate()[0]).strip()
                if '-' in hostname:
                    hostname = hostname.rsplit('-', 1)[0]

                group_value = config_data["autoscale_groups"][hostname]
                as_group = hostname
            except Exception, e:
                logger.debug("Failed to get hostname: %s" % str(e))
                logger.warning("Multiple group found in config file, "
                               "please use 'as-group' option")
                exit_with_error('Unable to identify targeted group')
    else:
        try:
            group_value = config_data["autoscale_groups"][args['as_group']]
            as_group = args['as_group']
        except:
            exit_with_error("Unable to find group '" + args['as_group'] +
                            "' in " + config_file)

    username = common.get_user_value(args, config_data, 'os_username')
    if username is None:
        exit_with_error(None)
    api_key = common.get_user_value(args, config_data, 'os_password')
    if api_key is None:
        exit_with_error(None)
    region = common.get_user_value(args, config_data, 'os_region_name')
    if region is None:
        exit_with_error(None)

    session = Auth(username, api_key, region)

    if session.authenticate() is True:
        rv = autoscale(as_group, config_data, args)
        if rv is None:
            log_file = None
            if hasattr(logger.root.handlers[0], 'baseFilename'):
                log_file = logger.root.handlers[0].baseFilename
            if log_file is None:
                logger.info('completed successfull')
            else:
                logger.info('completed successfully: %s' % log_file)
        else:
            exit_with_error(None)
    else:
        exit_with_error('Authentication failed')


if __name__ == '__main__':
    main()
