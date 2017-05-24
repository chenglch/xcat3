# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 International Business Machines Corporation
# Updated 2017 for xcat test purpose
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
from oslo_utils import fileutils

from xcat3.common import exception
from xcat3.network import base_manager
from xcat3 import objects
from xcat3.common import ip_lib
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.network import dhcp

MANAGER_TOPIC = 'xcat3.network_manager'
XCAT3_RUN_PATH = '/var/run/xcat3'

LOG = log.getLogger(__name__)


class NetworkManager(base_manager.BaseServiceManager):
    """XCAT3 Conductor manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(NetworkManager, self).__init__(host, topic)
        fileutils.ensure_tree(XCAT3_RUN_PATH)
        self.dhcp_service = dhcp.ISCDHCPService()
        self._restart_dhcp()

    def _restart_dhcp(self):
        networks = objects.Network.list(context=None)
        ip_wappter = ip_lib.IPWrapper()
        self.dhcp_service.clear_subnet()
        for network in networks:
            subnet = network.subnet
            netmask = network.netmask
            ifaces = ip_wappter.get_devices_in_network(subnet, netmask)
            if not ifaces:
                error = _("Can not find correct network interfaces for subnet "
                          "%(subnet)s netmask %(netmask)s") % {
                            'subnet': subnet, 'netmask': netmask}
                LOG.warning(error)
                continue
            nic_ip = ifaces[0].devices_ips()[0]
            opts = dict()
            opts['nic'] = ifaces[0].name
            # test jinja2, check 'if' statement works in templdate
            # opts['dynamic_range'] = network.dynamic_range
            opts['subnet'] = subnet
            opts['netmask'] = netmask
            opts['netbits'] = ip_wappter.get_net_bits(netmask)
            opts['conductor'] = nic_ip
            opts['next_server'] = nic_ip
            opts['router'] = network.gateway or nic_ip
            opts['domain_name'] = network.domain
            opts['domain_name_servers'] = network.nameservers
            opts['domain_search'] = network.domain
            opts['subnet_id'] = network.id
            network_opts = {"network": opts}
            self.dhcp_service.add_subnet(network_opts)
        # restart will be invoked in build_conf subroutine
        self.dhcp_service.build_conf()
        self.dhcp_service.restart()

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker)
    def restart_dhcp(self, context):
        """RPC method to restart dhcp server

        When network configuration is changed, this method should be called

        :param context: an admin context.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info(_("Restarting dhcp server. "))
        self._restart_dhcp()

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker)
    def check_support(self, context, subnet=None):
        """RPC method to check if the subnet opts is supported

        :param context: an admin context.
        :param subnet: network object
        :returns: True if support, False if not support
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        subnet_opts = self.dhcp_service.get_subnet_opts()
        if not subnet_opts or not self.dhcp_service.status():
            return False

        if not subnet:
            return True

        LOG.info(_("Check if subnet %(subnet)s is supported by dhcp service")
                 % {'subnet': subnet.name})

        self.dhcp_service.get_subnet_opts()
        for opt in self.dhcp_service.get_subnet_opts():
            if opt.get('network').get('subnet_id') == subnet.id:
                return True
        return False

    @messaging.expected_exceptions(exception.NoFreeServiceWorker,
                                   exception.DHCPProcessError)
    def enable_dhcp_option(self, context, subnet=None):
        """RPC method to enable dhcp options

        :param context: an admin context.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """
        LOG.info(_LI('Enable dhcp service for request '
                     '%s' % context.request_id))
        self.dhcp_service.build_conf()
        self.dhcp_service.restart()
