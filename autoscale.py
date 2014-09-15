import common
import pyrax
import argparse
import time
import os

def autoscale(group, config, cluster_mode):
  au = pyrax.autoscale
  cm = pyrax.cloud_monitoring

  group_id = config.get(group, 'id')
  
  sgs = au.list()

  # Find scaling group from config
  for pos, sg in enumerate(sgs):
    if sg.id == group_id:
      break
  
  if sg is None:
    common.log('ERROR', 'ScalingGroup not found')
    exit(1)
  
  sg_state = sg.get_state()
  
  # Make sure there is atleast one instance in the AS group, if < 1 we cannot gauge the metrics of nothing
  if sg_state['active_capacity'] < 1:
    common.log('ERROR', '0 Servers present in scaling group invalid configuration, exiting')
    exit(1)

  common.log('INFO', 'Current Active Servers: ' + str(sg_state['active_capacity']))
  common.log('INFO', 'Cluster Mode Enabled: ' + str(cluster_mode))

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
      common.log('ERROR', 'Unknown cluster state')
      exit(1)

    if node_id in masters:
      common.log('INFO', 'Node is a master, continuing')
    else:
      common.log('INFO', 'Node is not a master, nothing to do. Exiting')
      exit(0)

  # Gather cluster statistics
  check_type = config.get(group, 'check_type', 'agent.load_average')
  metric_name = config.get(group, 'metric_name', '1m')
  
  common.log('INFO', 'Gathering Monitoring Data')

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
            common.log('INFO', 'Found metric for: ' + ent.name + ', value: ' + str(data[point]['average']))
            results.append(float(data[point]['average']))
            break

  if len(results) == 0:
    common.log('ERROR', 'No data available')
    exit(1)
  else:
    average = sum(results)/len(results)
    scale_up_threshold = config.getfloat(group, 'scale_up_threshold')
    scale_down_threshold = config.getfloat(group, 'scale_down_threshold')
   
    common.log('INFO', 'Cluster average for ' + check_type + '(' + metric_name + ') at: ' + str(average))
    
    if average > scale_up_threshold:
      try:
        common.log('INFO', 'Above Threshold - Scaling Up')
        scale_policy = sg.get_policy(config.get(group, 'scale_up_policy'))
        scale_policy.execute()
      except:
        common.log('ERROR', 'Cannot execute scale up policy')
    elif average < scale_down_threshold:
      try:
        common.log('INFO', 'Below Threshold - Scaling Down')
        scale_policy = sg.get_policy(config.get(group, 'scale_down_policy'))
        scale_policy.execute()
      except:
        common.log('ERROR', 'Cannot execute scale down policy')
    else:
      common.log('INFO', 'Cluster within target paramters')
    
    common.log('OK', 'Policy execution completed')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--region', required=False,
    help='The region to build the servers',
    choices=['SYD', 'HKG', 'DFW', 'ORD', 'IAD', 'LON'],
    default=pyrax.default_region)
  parser.add_argument('--as-group', required=True,
    help='The autoscale group config ID')
  parser.add_argument('--cluster', required=False, default=False, action='store_true')

  args = vars(parser.parse_args())
  common.authenticate(args['region'])

  try:
    config = common.get_config(args['as_group'])
  except:
    common.log('ERROR', 'Unknown config section ' + args['as_group'])
  
  autoscale(args['as_group'], config, args['cluster'])
