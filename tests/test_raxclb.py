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

import unittest

from mock import MagicMock, patch
from pyrax.exceptions import NotFound
from pyrax.cloudloadbalancers import CloudLoadBalancer

from raxas.core_plugins.raxclb import Raxclb


class RaxclbTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(RaxclbTest, self).__init__(*args, **kwargs)
        self.config = {'raxclb': {}}
        self.args = {}

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_no_lb(self, mock_clb, mock_au):
        mock_au.scalingGroup.get_launch_config.return_value = {'test': 'case'}
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)

        self.assertIsNone(rclb.make_decision())

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_bad_lb(self, mock_clb, mock_au):
        mock_au.scalingGroup.state.activeCapacity.return_value = 1
        self.config = {'raxclb': {'loadbalancers': ['doesnotexist']}}
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)
        mock_clb.get.side_effect = NotFound(404)

        self.assertIsNone(rclb.make_decision())

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_scaleup(self, mock_clb, mock_au):
        mock_au.scalingGroup.state.__getitem__.return_value = 1
        mock_au.scalingGroup.get_launch_config.return_value = \
            {'load_balancers': [{'loadBalancerId': 231231}]}
        fakelb = MagicMock(spec=CloudLoadBalancer)
        fakelb.get_stats.return_value = {'currentConn': 100}
        mock_clb.get.return_value = fakelb
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)

        self.assertEqual(1, rclb.make_decision())

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_scaledown(self, mock_clb, mock_au):
        mock_au.scalingGroup.state.__getitem__.return_value = 1
        mock_au.scalingGroup.get_launch_config.return_value = \
            {'load_balancers': [{'loadBalancerId': 231231}]}
        fakelb = MagicMock(spec=CloudLoadBalancer)
        fakelb.get_stats.return_value = {'currentConn': 0}
        mock_clb.get.return_value = fakelb
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)
        self.assertEqual(-1, rclb.make_decision())

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_donothing(self, mock_clb, mock_au):
        mock_au.scalingGroup.state.__getitem__.return_value = 1
        mock_au.scalingGroup.get_launch_config.return_value = \
            {'load_balancers': [{'loadBalancerId': 231231}]}
        fakelb = MagicMock(spec=CloudLoadBalancer)
        fakelb.get_stats.return_value = {'currentConn': 20}
        mock_clb.get.return_value = fakelb
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)
        self.assertEqual(0, rclb.make_decision())

    @patch('pyrax.autoscale')
    @patch('pyrax.cloud_loadbalancers', create=True)
    def test_make_decision_ssl(self, mock_clb, mock_au):
        mock_au.scalingGroup.state.__getitem__.return_value = 1
        mock_au.scalingGroup.get_launch_config.return_value = \
            {'load_balancers': [{'loadBalancerId': 231231}]}
        fakelb = MagicMock(spec=CloudLoadBalancer)
        fakelb.get_stats.return_value = {'currentConnSsl': 20}
        fakelb.get_usage.return_value = {
            'loadBalancerUsageRecords': [
                {'averageNumConnectionsSsl': 5},
                {'averageNumConnectionsSsl': 8}
            ]
        }
        mock_clb.get.return_value = fakelb
        self.config = {'raxclb': {'check_type': 'ssl'}}
        rclb = Raxclb(mock_au.scalingGroup, self.config, self.args)
        self.assertEqual(0, rclb.make_decision())
