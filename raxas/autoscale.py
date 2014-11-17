#!/usr/bin/env python
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

import common
import pyrax
import argparse
import time
import os
import sys
import logging.config
from colouredconsolehandler import ColouredConsoleHandler
from auth import Auth
import cloudmonitor
from version import return_version
import json
import urllib2


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


def webhook_call(config, group, policy, key):

    url_list = common.get_webhook_value(config_data, group, policy)
    if url_list is None:
        logger.error('Unable to get webhook urls from json file')
        return

    group_id = common.get_group_value(config_data, group, 'GROUP_ID')
    if group_id is None:
        logger.error('Unable to get GROUP_ID from json file')
        return

    up_policy_id = common.get_group_value(config_data, group,
                                          'SCALE_UP_POLICY')
    if up_policy_id is None:
        logger.error('Unable to get SCALE_UP_POLICY from json file')
        return

    down_policy_id = common.get_group_value(config_data, group,
                                            'SCALE_DOWN_POLICY')
    if down_policy_id is None:
        logger.error('Unable to get SCALE_DOWN_POLICY from json file')
        return

    check_type = common.get_group_value(config_data, group, 'CHECK_TYPE')
    if check_type is None:
        logger.error('Unable to get CHECK_TYPE from json file')
        return

    metric_name = common.get_group_value(config_data, group,
                                         'METRIC_NAME')
    if check_type is None:
        logger.error('Unable to get METRIC_NAME from json file')
        return

    up_threshold = common.get_group_value(config_data, group,
                                          'SCALE_UP_THRESHOLD')
    if up_threshold is None:
        logger.error('Unable to get SCALE_UP_THRESHOLD from json file')
        return

    down_threshold = common.get_group_value(config_data, group,
                                            'SCALE_DOWN_THRESHOLD')
    if up_threshold is None:
        logger.error('Unable to get SCALE_DOWN_THRESHOLD from json file')
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


def exit_with_error(msg):
    if msg is None:
        try:
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: ' + log_file)
        except:
            print ('(info) rax-autoscale completed with an error')
    else:
        try:
            logger.error(msg)
            log_file = logger.root.handlers[0].baseFilename
            logger.info('completed with an error: ' + log_file)
        except:
            print ('(error) ' + msg)
            print ('(info) rax-autoscale completed with an error')

    exit(1)


def is_node_master(scalingGroup):
    masters = []
    node_id = common.get_machine_uuid()
    sg_state = scalingGroup.get_state()
    if len(sg_state['active']) == 1:
        masters.push(sg_state['active'][0])
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

    group_id = common.get_group_value(config_data, group, 'GROUP_ID')
    if group_id is None:
        logger.error('Unable to get GROUP_ID from json file')
        return

    scalingGroup = cloudmonitor.scaling_group_servers(group_id)
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
    au = pyrax.autoscale

    scalingGroup = get_scaling_group(group, config_data)
    if scalingGroup is None:
        return 1

    for s_id in scalingGroup.get_state()['active']:
        rv = cloudmonitor.add_cm_cpu_check(s_id)

    logger.info('Cluster Mode Enabled: ' + str(args['cluster']))

    if args['cluster']:
        rv = is_node_master(scalingGroup)
        if rv is None:
            # Not a master, no need to proceed further
            return
        if rv == 1:
            # Cluster state unknown return error.
            return 1

    # Gather cluster statistics
    check_type = common.get_group_value(config_data, group, 'CHECK_TYPE')
    if check_type is None:
        check_type = 'agent.load_average'

    metric_name = common.get_group_value(config_data, group, 'METRIC_NAME')
    if metric_name is None:
        metric_name = '1m'

    logger.info('Gathering Monitoring Data')

    results = []
    cm = pyrax.cloud_monitoring
    # Get all CloudMonitoring entities on the account
    entities = cm.list_entities()
    # TODO: spawn threads for each valid entity to make data collection faster
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

    if len(results) == 0:
        logger.error('No data available')
        return 1
    else:
        average = sum(results)/len(results)
        scale_up_threshold = common.get_group_value(config_data, group,
                                                    'SCALE_UP_THRESHOLD')
        if scale_up_threshold is None:
            scale_up_threshold = 0.6

    scale_down_threshold = common.get_group_value(config_data, group,
                                                  'SCALE_DOWN_THRESHOLD')
    if scale_down_threshold is None:
        scale_down_threshold = 0.4

    logger.info('Cluster average for ' + check_type +
                '(' + metric_name + ') at: ' + str(average))

    if average > scale_up_threshold:
        try:
            logger.info('Above Threshold - Scaling Up')
            scale_policy_id = common.get_group_value(config_data, group,
                                                     'SCALE_UP_POLICY')
            scale_policy = scalingGroup.get_policy(scale_policy_id)
            if not args['dry_run']:
                webhook_call(config_data, group, 'SCALE_UP', 'PRE')
                scale_policy.execute()
                webhook_call(config_data, group, 'SCALE_UP', 'POST')
            else:
                logger.info('Scale up prevented by --dry-run')
                logger.info('Scale up policy executed ('
                            + scale_policy_id + ')')
        except:
            logger.warning('Cannot execute scale up policy')
    elif average < scale_down_threshold:
        try:
            logger.info('Below Threshold - Scaling Down')
            scale_policy_id = common.get_group_value(config_data, group,
                                                     'SCALE_DOWN_POLICY')
            scale_policy = scalingGroup.get_policy(scale_policy_id)
            if not args['dry_run']:
                webhook_call(config_data, group, 'SCALE_DOWN', 'PRE')
                scale_policy.execute()
                webhook_call(config_data, group, 'SCALE_DOWN', 'POST')
            else:
                logger.info('Scale down prevented by --dry-run')
                logger.info('Scale down policy executed (' +
                            scale_policy_id + ')')

        except:
            logger.warning('Cannot execute scale down policy')

    else:
        logger.info('Cluster within target paramters')


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--as-group', required=True,
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

    args = vars(parser.parse_args())

    # CONFIG.ini
    config_file = common.check_file(args['config_file'])
    if config_file is None:
        exit_with_error("Either file is missing or is not readable: '" +
                        args['config_file']+"'")

    # Show Version
    logger.info(return_version())

    for arg in args:
        logger.debug('argument provided by user ' + arg + ' : ' +
                     str(args[arg]))

    # Get data from config.json
    config_data = common.get_config(config_file)
    if config_data is None:
        exit_with_error('Failed to read config file: ' + config_file)

    # Check if group exists
    try:
        group_value = config_data["AUTOSCALE_GROUPS"][args['as_group']]
    except:
        exit_with_error("Unable to find group '" + args['as_group'] +
                        "' in " + config_file)

    failed = 0
    try:
        username = common.get_user_value(args, config_data, 'os_username')
        api_key = common.get_user_value(args, config_data, 'os_password')
        region = common.get_user_value(args, config_data, 'os_region_name')
    except Exception, err:
        logger.error(err)
        failed = 1

    if failed == 0:
        session = Auth(username, api_key, region)

    if session.authenticate() is True:
        rv = autoscale(args['as_group'], config_data, args)
        if rv is None:
            log_file = None
            if hasattr(logger.root.handlers[0], 'baseFilename'):
                log_file = logger.root.handlers[0].baseFilename
            if log_file is None:
                logger.info('completed successfull')
            else:
                logger.info('completed successfully: '+log_file)
        else:
            exit_with_error('Unable to proceed further')
    else:
        exit_with_error('Authentication failed')


if __name__ == '__main__':
    main()
