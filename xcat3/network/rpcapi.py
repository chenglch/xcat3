# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
"""
Client side of the conductor RPC API.
"""

import futurist
from futurist import rejection
import retrying
import oslo_messaging as messaging
from oslo_log import log

from xcat3.common import exception
from xcat3.common import rpc
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.network import manager
from xcat3.conf import CONF
from xcat3.db import api as dbapi
from xcat3.objects import base as objects_base

LOG = log.getLogger(__name__)


class NetworkAPI(object):
    """Client side of the conductor RPC API.
    """
    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(NetworkAPI, self).__init__()
        self.topic = topic
        self.dbapi = dbapi.get_instance()
        if self.topic is None:
            self.topic = manager.MANAGER_TOPIC

        target = messaging.Target(topic=self.topic,
                                  version='1.0')
        serializer = objects_base.XCAT3ObjectSerializer()
        self.client = rpc.get_client(target,
                                     version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)
        rejection_func = rejection.reject_when_reached(
            CONF.network.workers_pool_size)
        self._executor = futurist.GreenThreadPoolExecutor(
            max_workers=CONF.network.workers_pool_size,
            check_and_reject=rejection_func)

    def broadcast(self, context):
        """If network information is changed, notify the network worker"""
        services = self.dbapi.get_services(type='network')
        for s in services:
            topic = '%s.%s' % (self.topic, s.hostname.encode('utf-8'))
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            cctxt.cast(context, 'restart_dhcp')

    def get_topic_for(self, context, subnet=None):
        """Get the RPC topic for the network service the nodes are mapped to.

        :param context: request context.
        :param subnet: subnet in network object
        :returns: an RPC topic for all the network nodes
        :raises: NoValidHost

        """
        services = self.dbapi.get_services(type='network')
        if not services:
            reason = (_('No network service registered'))
            raise exception.NoValidHost(reason=reason)

        for s in services:
            topic = '%s.%s' % (self.topic, s.hostname.encode('utf-8'))
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            if cctxt.call(context, 'check_support', subnet=subnet):
                return topic
        if subnet:
            reason = (_('Could not find network service support subnet '
                        '%(subnet)s') % {'subnet': subnet.name})
        else:
            reason = (_('Could not find available network service, please '
                        'check network object.'))
        raise exception.NoValidHost(reason=reason)

    def update_dhcp(self, context, op, names, dhcp_opts, subnet=None):
        """Update dhcp options for node .

        :param context: request context.
        :param names: names of nodes.
        :param dhcp_opts: dhcp options for each node.
        :param subnet: subnet object, used to determine the target network
                       service node.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.

        """
        topic = self.get_topic_for(context, subnet)
        cctxt = self.client.prepare(topic=topic or self.topic,
                                    version='1.0')
        # NOTE(chenglch): subnet has been used to select the target network
        # service node, no need to transfer the subnet object with the rpc call
        # again.
        cctxt.cast(context, 'update_dhcp', op=op, names=names,
                   dhcp_opts=dhcp_opts)

    @retrying.retry(
        retry_on_result=lambda r: not r,
        stop_max_attempt_number=CONF.network.dhcp_check_attempts,
        wait_fixed=CONF.network.dhcp_check_retry_interval * 1000)
    def check_dhcp_complete(self, context, subnet=None):
        """RPC method to check the complete status for the request

        :param context: an admin context.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """
        LOG.info(_LI('Check the dhcp complete status for request '
                     '%s' % context.request_id))
        topic = self.get_topic_for(context, subnet)
        cctxt = self.client.prepare(topic=topic or self.topic,
                                    version='1.0')
        return cctxt.call(context, 'check_dhcp_complete')

    def enable_dhcp_option(self, context, subnet=None):
        """RPC method to enable dhcp options

        :param context: an admin context.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: DHCPProcessError if dhcp server can not be started.
        """
        LOG.info(_LI('Enable dhcp service for request '
                     '%s' % context.request_id))
        topic = self.get_topic_for(context, subnet)
        cctxt = self.client.prepare(topic=topic or self.topic,
                                    version='1.0')
        cctxt.call(context, 'enable_dhcp_option')
