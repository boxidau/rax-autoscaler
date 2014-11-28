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

import datetime
import logging
import pyrax

# GLOBALS
d_cached_servers_name = {}  # cached dictionary of server id:name
check_name = 'raxas'


def add_cm_check(server_id, check_type, check_config):
    """This function adds Cloud Monitoring cpu check to a server,
       if it is not already present

    :param server_id: server identity
    :type name: str
    :returns: int -- the return code
                1 -- Success
    """
    logger = logging.getLogger(__name__)
    global check_name
    try:
        entity = get_entity(server_id)

        # check if the check already exists
        exist_check = len([c for c in entity.list_checks()
                          if c.type == check_type])

        # add check if it does not exist
        ip_address = get_server_ipv4(server_id, _type='private')
        logger.debug("server_id:%s, ip_address:%s, type:private" %
                     (server_id, ip_address))
        if not exist_check:
            cm = pyrax.cloud_monitoring
            chk = cm.create_check(entity,
                                  label=check_name + '_' + check_type,
                                  check_type=check_type,
                                  details=check_config,
                                  period=60, timeout=30,
                                  target_alias=ip_address)
            logging.info('ADD - Cloud monitoring check (' + check_type +
                         ') to server with id: ' + server_id)
        else:
            logging.info('SKIP - Cloud monitoring check (' + check_type +
                         ') already exists on server id: ' + server_id)
        return 1

    except:
        logging.warning('Unable to add cloud monitoring check (' + check_type +
                        ') to server with id: ' + server_id)
        return


def get_entity(agent_id):
    """This function get entity for passed agent_id (agent_id := server_uuid)

    :param agent_id: agent id
    :type name: str

    """
    cm = pyrax.cloud_monitoring
    try:
        return filter(lambda e: e.agent_id == agent_id,
                      [e for e in cm.list_entities()])[0]
    except:
        logging.info('no entity with agent_id: %s' % agent_id)
        return None


def get_server(server_id):
    """ It gets Cloud server object by server_id

    """
    cs = pyrax.cloudservers
    try:
        return filter(lambda s: s.id == server_id, [s for s in cs.list()])[0]
    except:
        logging.info('no cloud server with id: %s' % server_id)
        return None


def get_server_name(server_id):
    """It returns the name of a server, using cached values

    :param server_id: server id
    :type name: str
    :returns: d_cached_servers_name[server_id] (str)

    """
    global d_cached_servers_name

    try:
        # try returning name from cache

        return d_cached_servers_name[server_id]

    except KeyError:
        # ask Rackspace API
        server = get_server(server_id)
        if server is None:
            return None
        else:
            d_cached_servers_name[server_id] = server.name
            return d_cached_servers_name[server_id]


def scaling_group_servers(sgid):
    """ list servers' id in scaling group sgid

    :param sgid: scaling group id
    :type name: str

    """
    a = pyrax.autoscale
    try:
        sg = a.get(sgid)
        return sg
    except:
        logging.error('Unable to find scaling group with id:%s' % sgid)
        return


def get_server_ipv4(server_id, _type='public'):
    """ It gets public IP v4 server address

    :param server_id: server id
    :type name: str

    """
    server = get_server(server_id)
    if server is None:
        return None
    try:
        return [i for i in server.networks[_type] if is_ipv4(i)][0]
    except KeyError:
        msg = 'server (%s) has no network %s' % (server_id, _type)
        logging.warning(msg)
        return None


def is_ipv4(address):
    """It checks if address is valid IP v4

    """
    import socket
    try:
        socket.inet_aton(address)
        return True
    except socket.error:
        return False
