# RAX-AutoScaler

Uses the rackspace APIs to allow for scaling based on aggregate metrics across a cluster.
Can be used and installed on the auto-scale group members or on a dedicated management instance.

- [GitHub repository](https://github.com/boxidau/rax-autoscaler)
- [PyPI package](https://pypi.python.org/pypi/rax-autoscaler)

[![Stories in Ready](https://badge.waffle.io/boxidau/rax-autoscaler.svg?label=ready&title=Ready)](http://waffle.io/boxidau/rax-autoscaler)

**ATTENTION!** *rax-autoscaler* is in a very early development stage.

## Installation

```
pip install RAX-AutoScaler
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
Once configured you can invoke the autoscaler.py script with the following required argument ```--as-group```:

- ```--as-group``` must refer to a section in the config.json file

You can also invoke the script with the --cluster option this should be used when this script actually runs on auto-scale group members. Otherwise if it is running on a dedicated management instance you do not require this option.

Once tested you should configure this script to run as a cron job either on a management instance or on all cluster members

### Note

RAX-AutoScaler depends on Rackspace Monitoring Agent to get the data from nodes in scaling group.
If the agent is not installed please read: [Install the Cloud Monitoring Agent](http://www.rackspace.com/knowledge_center/article/install-the-cloud-monitoring-agent)

## Contributing

- Fork it
- Create your feature branch (git checkout -b my-new-feature)
- Commit your changes (git commit -am 'Add some feature')
- Push to the branch (git push origin my-new-feature)
- Create new Pull Request

## License

```
Copyright 2014 Rackspace US, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

