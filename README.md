rax-autoscaler
==============

Uses the rackspace APIs to allow for scaling based on aggregate metrics across a cluster.
Can be used and installed on the auto-scale group members or on a dedicated management instance.

## Installation
```
git clone git@github.com:boxidau/rax-autoscaler.git
virtualenv rax-autoscaler
cd rax-autoscaler/
source bin/activate
pip install pyrax termcolor netifaces six requests python-novaclient argparse
cp config-template.json config.json
```

### Configuration
Edit config.json adding the following:
 - API username 
 - API key
 - Region name
 - Autoscaling group section should contain:
    - AutoScale Group UUID
    - Scale Up Policy UUID
    - Scale Down Policy UUID
    - Check Type (agent.cpu, agent.load_average...)
    - Metric Name (depends on the check type)
    - Scale Up Threshold
    - Scale Down Threshold
    - Webhooks Url (Pre & Post commit url(s) for scale up/down)

## Usage
Once configured you can invoke the autoscaler.py script with the following required argument --as-group
 - --as-group must refer to a section in the config.json file

You can also invoke the script with the --cluster option this should be used when this script actually runs on auto-scale group members. Otherwise if it is running on a dedicated management instance you do not require this option.

Once tested you should configure this script to run as a cron job either on a management instance or on all cluster members

### Note
rax-autoscaler depend on rackspace monitoring agent to get the data from nodes in scaling group. If the agent is not installed please follow : http://www.rackspace.com/knowledge_center/article/install-the-cloud-monitoring-agent
