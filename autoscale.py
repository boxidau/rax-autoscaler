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
      logger.info('completed with an error: '+ log_file)
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

def get_scaling_group(group, config):
  scalingGroup = cloudmonitor.scaling_group_servers(config.get(group, 'GROUP_ID'))
  # Check active server(s) in scaling group
  if len(scalingGroup.get_state()['active']) == 0:
    return
  else:
    logger.info('Server(s) in scaling group: %s' %
                  ', '.join(['(%s, %s)' % (cloudmonitor.get_server_name(s_id), s_id)
                                        for s_id in scalingGroup.get_state()['active']]))
    logger.info('Current Active Servers: ' + str(scalingGroup.get_state()['active_capacity']))
    return scalingGroup

def autoscale(group, config, cluster_mode):
  au = pyrax.autoscale

  scalingGroup = get_scaling_group(group, config)
  if scalingGroup is None:
      return 1
   
  for s_id in scalingGroup.get_state()['active']:
    #TODO: Handle issue with server id for which cloud monitoring add check return null
    rv = cloudmonitor.add_cm_cpu_check(s_id)
   
  logger.info('Cluster Mode Enabled: ' + str(cluster_mode))

  if cluster_mode:
    rv = is_node_master(scalingGroup)
    if rv is None :
       #Not a master, no need to proceed further
       return
    if rv == 1 :
        #Cluster state unknown return error.
        return 1 

  # Gather cluster statistics
  check_type = config.get(group, 'CHECK_TYPE', 'agent.load_average')
  metric_name = config.get(group, 'METRIC_NAME', '1m')

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
          data = check.get_metric_data_points(metric_name, int(time.time())-300, int(time.time()), points=2)
          if len(data) > 0:
            point = len(data)-1
            logger.info('Found metric for: ' + ent.name + ', value: ' + str(data[point]['average']))
            results.append(float(data[point]['average']))
            break

  if len(results) == 0:
    logger.error('No data available')
    return 1
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
  parser.add_argument('--config-file', required=False, default='config.ini', help='The autoscale configuration .ini file (default:config.ini)'),
  parser.add_argument('--os-region-name', required=False, help='The region to build the servers',
  choices=['SYD', 'HKG', 'DFW', 'ORD', 'IAD', 'LON'])
  parser.add_argument('--cluster', required=False, default=False, action='store_true')

  args = vars(parser.parse_args())
  
  #CONFIG.ini
  config_file = common.check_file(args['config_file'])
  if config_file is None:
    exit_with_error("Either file is missing or is not readable: '" + args['config_file']+"'")

  #LOGGING
  logging_conf_file = 'logging.conf'   
  logging.handlers.ColouredConsoleHandler = ColouredConsoleHandler
  logging.config.fileConfig(logging_conf_file)
  logger = logging.getLogger(__name__)

  for arg in args:
    logger.debug('argument provided by user ' + arg + ' : ' + str(args[arg]))
  
  try:
    config = common.get_config(config_file, args['as_group'])
  except:
    exit_with_error('Unknown config section ' + args['as_group'])

  failed = 0 
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
        rv = autoscale(args['as_group'], config, args['cluster'])
        if rv is None:
          log_file = logger.root.handlers[0].baseFilename
          if log_file is None:
            logger.info('completed successfull')
          else:  
            logger.info('completed successfully: '+log_file)
        else:
          exit_with_error()
    else:
      exit_with_error('Authentication failed')
