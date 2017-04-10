# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 International Business Machines Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Conduct all activity related to bare-metal deployments.

"""

from oslo_log import log
import oslo_messaging as messaging
from futurist import waiters

from xcat3.common import exception
from xcat3.dhcp import base_manager
from xcat3.conf import CONF
from xcat3 import objects
from xcat3.common import states as xcat3_states
from xcat3.common import ip_lib
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.dhcp import dhcp
from xcat3.plugins import mapping

MANAGER_TOPIC = 'xcat3.dhcp_manager'

LOG = log.getLogger(__name__)


class ConductorManager(base_manager.BaseConductorManager):
    """XCAT3 Conductor manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(ConductorManager, self).__init__(host, topic)
        self.dhcp_service = dhcp.ISCDHCPService()

    def _build_subnet_opts(self, context):
        networks = objects.Network.list(context)

        ip_wappter = ip_lib.IPWrapper()
        for network in networks:
            subnet = network.subnet
            netmask = network.netmask
            ifaces = ip_wappter.get_devices_in_network(subnet, netmask)
            if not ifaces:
                continue
            nic_ip = ifaces[0].devices_ips()[0]
            opts = dict()
            opts['nic'] = ifaces[0].name

            opts['subnet'] = subnet
            opts['netmask'] = netmask
            opts['netbits'] = ip_wappter.get_net_bits(netmask)
            opts['conductor'] = '10.4.40.22'
            opts['nextserver'] = nic_ip
            opts['router'] = nic_ip
            network_opts = {"network": opts}
            self.dhcp_service.add_subnet(network_opts)
        self.dhcp_service.build_conf()

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeConductorWorker,
                                   exception.NodeLocked)
    def provision(self, context, names, target):
        """RPC method to encapsulate changes to a node's state.

        :param context: an admin context.
        :param names: the names of nodes.
        :param target: the desired power state of the node.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC provision at dhcp conductor called for nodes %(nodes)s. "
                 "The desired new state is %(target)s.",
                 {'nodes': str(names), 'target': target})

        self._build_subnet_opts(context)
        self.dhcp_service.restart()
