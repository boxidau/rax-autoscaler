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
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging.config
import socket

from raxas import common, enums
from raxas.colouredconsolehandler import ColouredConsoleHandler
from raxas.auth import Auth
from raxas.version import return_version
from raxas.core_plugins.raxmon import Raxmon


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


def is_node_master(scalingGroup):
    """This function checks scaling group state and determines if node is a master.

    :param scalingGroup: data about servers in scaling group retrieve from cloudmonitor
    :returns: enums.NodeStatus

    """
    masters = []
    node_id = common.get_machine_uuid(scalingGroup)

    if node_id is None:
        logger.error('Failed to get server uuid')
        return enums.NodeStatus.Unknown

    sg_state = scalingGroup.get_state()
    if len(sg_state['active']) == 1:
        masters.append(sg_state['active'][0])
    elif len(sg_state['active']) > 1:
        masters.append(sg_state['active'][0])
        masters.append(sg_state['active'][1])
    else:
        logger.error('Unknown cluster state')
        return enums.NodeStatus.Unknown

    if node_id in masters:
        logger.info('Node is a master, continuing')
        return enums.NodeStatus.Master
    else:
        logger.info('Node is not a master, nothing to do. Exiting')
        return enums.NodeStatus.Slave


def autoscale(group, config_data, args):
    """This function executes scale up or scale down policy

    :param group: group name
    :param config_data: json configuration data
    :param args: user provided arguments
    :returns: enums.ScaleEvent
    """

    scalingGroup = common.get_scaling_group(group, config_data)
    if scalingGroup is None:
        logger.error('Unable to get scaling group: %s', group)
        return enums.ScaleEvent.Error

    logger.info('Cluster Mode Enabled: %s', args.get('cluster', False))

    if args['cluster']:
        is_master = is_node_master(scalingGroup)
        if is_master in [enums.NodeStatus.Slave, enums.NodeStatus.Unknown]:
            return enums.ScaleEvent.NotMaster

    monitor = Raxmon(scalingGroup,
                     common.get_plugin_config(config_data, group, "raxmon"), args)

    scaling_decision = monitor.make_decision()
    if scaling_decision is None:
        return enums.ScaleEvent.Error
    elif scaling_decision <= -1:
        scaling_decision = -1
    elif scaling_decision >= 1:
        scaling_decision = 1

    scale = {-1: 'down', 1: 'up'}.get(scaling_decision, None)
    if scale is None:
        logger.info('Cluster within target parameters')
        return enums.ScaleEvent.NoAction

    try:
        logger.info('Threshold reached - Scaling %s', scale.title())
        scale_policy_id = common.get_group_value(config_data, group, 'scale_%s_policy' % scale)
        scale_policy = scalingGroup.get_policy(scale_policy_id)
        if not args['dry_run']:
            common.webhook_call(config_data, group, 'scale_%s' % scale, 'pre')
            scale_policy.execute()
            logger.info('Scale %s policy executed (%s)', scale, scale_policy_id)
            common.webhook_call(config_data, group, 'scale_%s' % scale, 'post')
        else:
            logger.info('Scale %s prevented by --dry-run', scale)

        return enums.ScaleEvent.Success
    except Exception as error:
        logger.error('Error scaling %s: %s', scale, error)
        return enums.ScaleEvent.Error


def parse_args():
    """This function validates user arguments and data in configuration file.

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
                             '(default: config.json)')
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

    return args


def main():
    """This function calls auth class for authentication and autoscale to
       execute scaling policy

    """
    args = parse_args()
    logger.info(return_version())
    for arg in args:
        logger.debug('argument provided by user ' + arg + ' : ' +
                     str(args[arg]))

    # CONFIG.ini
    config_file = common.check_file(args['config_file'])
    if config_file is None:
        common.exit_with_error('Either file is missing or is not readable: %s'
                               % args['config_file'])

    config_data = common.get_config(config_file)
    if config_data is None:
        common.exit_with_error('Failed to read config file: ' + config_file)

    as_group = args.get('as_group')
    if not as_group:
        if len(config_data['autoscale_groups'].keys()) == 1:
            as_group = config_data['autoscale_groups'].keys()[0]
        else:
            logger.debug("Getting system hostname")
            hostname = socket.gethostname()
            as_group = hostname.rsplit('-', 1)[0]

    username = common.get_user_value(args, config_data, 'os_username')
    api_key = common.get_user_value(args, config_data, 'os_password')
    region = common.get_user_value(args, config_data, 'os_region_name')
    if None in (username, api_key, region):
        common.exit_with_error('Authentication credentials not set')
    region = region.upper()

    session = Auth(username, api_key, region)
    if not session.authenticate():
        common.exit_with_error('Authentication failed')

    scale_result = autoscale(as_group, config_data, args)
    if scale_result == enums.ScaleEvent.Error:
        common.exit_with_error(None)
    else:
        log_name = None
        if hasattr(logger.root.handlers[0], 'baseFilename'):
            log_name = ': ' % logger.root.handlers[0].baseFilename
        logger.info('completed successfully %s', (log_name if log_name else ''))


if __name__ == '__main__':
    main()
