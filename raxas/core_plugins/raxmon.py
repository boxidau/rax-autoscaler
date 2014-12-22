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

import logging
import random
import time
import pyrax
import raxas.common as common


class Raxmon(object):

    def __init__(self, scaling_group, config, args):
        self.scaleup = config.get('scale_up_threshold', 0.6)
        self.scaledown = config.get('scale_down_threshold', 0.4)
        self.check_config = config.get('check_config', {})
        self.metric_name = config.get('metric_name', '1m')
        self.check_type = config.get('check_type', 'agent.load_average')
        self.scaling_group = scaling_group
        self.args = args

    def make_decision(self):
        """
        This function decides to scale up or scale down

        :returns: 1    scale up
                  0    do nothing
                 -1    scale down
                  None No data available
        """
        logger = logging.getLogger(__name__)

        for s_id in self.scaling_group.get_state()['active']:
            self.add_cm_check(s_id, self.metric_name, self.check_type, self.check_config)

        logger.info('Gathering Monitoring Data')

        results = []
        cm = pyrax.cloud_monitoring
        # Get all CloudMonitoring entities on the account
        entities = cm.list_entities()

        # Shuffle entities so the sample uses different servers
        entities = random.sample(entities, len(entities))

        for ent in entities:
            # Check if the entity is also in the scaling group
            if ent.agent_id in self.scaling_group.get_state()['active']:
                ent_checks = ent.list_checks()
                # Loop through checks to find checks of the correct type
                for check in ent_checks:
                    if check.type == self.check_type:
                        data = check.get_metric_data_points(self.metric_name,
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
            if len(results) >= self.args['max_sample']:
                logger.info('--max-sample value of ' + str(self.args['max_sample']) +
                            ' reached, not gathering any more statistics')
                break

        if len(results) == 0:
            logger.error('No data available')
            return None
        else:
            average = sum(results)/len(results)
            scale_up_threshold = self.scaleup
            if scale_up_threshold is None:
                scale_up_threshold = 0.6

        scale_down_threshold = self.scaledown
        if scale_down_threshold is None:
            scale_down_threshold = 0.4

        logger.info('Cluster average for ' + self.check_type +
                    '(' + self.metric_name + ') at: ' + str(average))

        if average > scale_up_threshold:
            logger.info("Raxmon reports scale up.")
            return 1
        elif average < scale_down_threshold:
            logger.info("Raxmon reports scale down.")
            return -1

        else:
            logger.info('Cluster within target paramters')
            return 0

    def add_cm_check(self, server_id, metric_name, check_type, check_config):
        """This function adds Cloud Monitoring cpu check to a server,
           if it is not already present

        :param server_id: server identity
        :type name: str
        :returns: int -- the return code
                    1 -- Success
        """
        logger = logging.getLogger(__name__)
        try:
            entity = self.get_entity(server_id)

            # check if the check already exists
            exist_check = len([c for c in entity.list_checks()
                               if c.type == check_type])

            # add check if it does not exist
            ip_address = common.get_server_ipv4(server_id, _type='private')
            logger.debug("server_id:%s, ip_address:%s, type:private" %
                         (server_id, ip_address))
            if not exist_check:
                cm = pyrax.cloud_monitoring
                chk = cm.create_check(entity,
                                      label=metric_name + '_' + check_type,
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

    def get_entity(self, agent_id):
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
