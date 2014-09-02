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
cp config.include config.ini
```

### Configuration
Edit config.ini adding the following:
 - API username and key
 - Scaling group section should contain:
    - AutoScale Group UUID
    - Scale Up Policy UUID
    - Scale Down Policy UUID
    - Check type (agent.cpu, agent.load_average...)
    - Metric name (depends on the check type)

## Usage
Once configured you can invoke the autoscaler.py script with the following required arguments --region and --as-group
 - --as-group must refer to a section in the config file
 - --region is the rackspace datacenter where the autoscale group exists (SYD, HKG, DFW, IAD, ORD, LON)

You can also invoke the script with the --cluster option this should be used when this script actually runs on auto-scale group members. Otherwise if it is running on a dedicated management instance you do not require this option.

Once tested you should configure this script to run as a cron job either on a management instance or on all cluster members
