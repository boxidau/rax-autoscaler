import common
import pyrax
import argparse
import time
import os
import sys
import logging.config
from colouredconsolehandler import ColouredConsoleHandler
from auth import Auth

def autoscale(group, config, cluster_mode):
  au = pyrax.autoscale
  cm = pyrax.cloud_monitoring

  group_id = config.get(group, 'GROUP_ID')
  
  sgs = au.list()

  # Find scaling group from config
  for pos, sg in enumerate(sgs):
    if sg.id == group_id:
      break
  
  if sg is None:
    logger.error('ScalingGroup not found')
    exit(1)
  
  sg_state = sg.get_state()
  
  # Make sure there is atleast one instance in the AS group, if < 1 we cannot gauge the metrics of nothing
  if sg_state['active_capacity'] < 1:
    logger.error('0 Servers present in scaling group invalid configuration, exiting')
    exit(1)

  logger.info('Current Active Servers: ' + str(sg_state['active_capacity']))
  logger.info('Cluster Mode Enabled: ' + str(cluster_mode))

  # cluster mode is when this script runs on all instances
  # rather than relying on cooldown periods we elect 2 masters from the AS group
  if cluster_mode:

    node_id = common.get_machine_uuid()
  
    masters = []

    if len(sg_state['active']) == 1:
      masters.push(sg_state['active'][0])
    elif len(sg_state['active']) > 1:
      masters.append(sg_state['active'][0])
      masters.append(sg_state['active'][1])
    else:
      logger.info('Unknown cluster state')
      exit(1)

    if node_id in masters:
      logger.info('Node is a master, continuing')
    else:
      logger.info('Node is not a master, nothing to do. Exiting')
      exit(0)

  # Gather cluster statistics
  check_type = config.get(group, 'CHECK_TYPE', 'agent.load_average')
  metric_name = config.get(group, 'METRIC_NAME', '1m')
  
  logger.info('Gathering Monitoring Data')

  results = []

  # Get all CloudMonitoring entities on the account
  entities = cm.list_entities()
  # TODO: spawn threads for each valid entity to make data collection faster
  for ent in entities:
    # Check if the entity is also in the scaling group
    if ent.agent_id in sg_state['active']:  
      ent_checks = ent.list_checks()
      # Loop through checks to find checks of the correct type
      for check in ent_checks:
        if check.type == check_type:
          data = check.get_metric_data_points(metric_name, int(time.time())-300, int(time.time()), points=2)
          if len(data) > 0:
            point = len(data)-1
            logger.info('Found metric for: ' + ent.name + ', value: ' + str(data[point]['average']))
            results.append(float(data[point]['average']))
            break

  if len(results) == 0:
    logger.error('No data available')
    exit(1)
  else:
    average = sum(results)/len(results)
    scale_up_threshold = config.getfloat(group, 'SCALE_UP_THRESHOLD')
    scale_down_threshold = config.getfloat(group, 'SCALE_DOWN_THRESHOLD')
   
    logger.info('Cluster average for ' + check_type + '(' + metric_name + ') at: ' + str(average))
    
    if average > scale_up_threshold:
      try:
        logger.info('Above Threshold - Scaling Up')
        scale_policy = sg.get_policy(config.get(group, 'SCALE_UP_POLICY'))
        scale_policy.execute()
      except:
        logger.warning('Cannot execute scale up policy')
    elif average < scale_down_threshold:
      try:
        logger.info('Below Threshold - Scaling Down')
        scale_policy = sg.get_policy(config.get(group, 'SCALE_DOWN_POLICY'))
        scale_policy.execute()
      except:
        logger.warning('Cannot execute scale down policy')
    else:
      logger.info('Cluster within target paramters')
    
    logger.info('Policy execution completed')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()

  parser.add_argument('--as-group', required=True, help='The autoscale group config ID')
  parser.add_argument('--os-username', required=False, help='Rackspace Cloud user name')
  parser.add_argument('--os-password', required=False, help='Rackspace Cloud account API key')
  parser.add_argument('--os-region-name', required=False, help='The region to build the servers',
  choices=['SYD', 'HKG', 'DFW', 'ORD', 'IAD', 'LON'])
  parser.add_argument('--cluster', required=False, default=False, action='store_true')

  args = vars(parser.parse_args())

  #LOGGING
  logging_conf_file = 'logging.conf'   
  logging.handlers.ColouredConsoleHandler = ColouredConsoleHandler
  logging.config.fileConfig(logging_conf_file)
  logger = logging.getLogger(__name__)
  
  for arg in args:
        if arg == 'cluster':
		if args[arg] == True: 
  			logger.debug('argument provided by user ' + arg + ' : ' + 'True')
	else:
        	if args[arg] != None:
  				logger.debug('argument provided by user ' + arg + ' : ' + args[arg])
	
  failed = 0 
  try:
    config = common.get_config(args['as_group'])
  except:
    logger.error('Unknown config section ' + args['as_group'])
    failed = 1
 
  try:
    username = common.get_user_value(args, config, 'os_username')
    api_key = common.get_user_value(args, config, 'os_password')
    region = common.get_user_value(args, config, 'os_region_name')
  except Exception, err:
    logger.error(err)
    failed = 1
  
  if failed == 0:
    session = Auth(username, api_key, region)
    
    if session.authenticate() == True:
      autoscale(args['as_group'], config, args['cluster'])
    else:
      logger.error('ERROR', 'Authentication failed')
