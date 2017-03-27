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
from futurist import waiters

import oslo_messaging as messaging

from xcat3.common import exception
from xcat3.common import rpc
from xcat3.dhcp import manager
from xcat3.conf import CONF
from xcat3.db import api as dbapi
from xcat3.objects import base as objects_base


class ConductorAPI(object):
    """Client side of the conductor RPC API.
    """
    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(ConductorAPI, self).__init__()
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
            CONF.dhcp.workers_pool_size)
        self._executor = futurist.GreenThreadPoolExecutor(
            max_workers=CONF.dhcp.workers_pool_size,
            check_and_reject=rejection_func)

    def get_topic_for(self):
        """Get the RPC topic for the conductor service the nodes are mapped to.

        :param nodes: the names of nodes
        :returns: an RPC topic string.
        :raises: NoValidHost

        """
        conductors = self.dbapi.get_conductors(service='dhcp')
        if not conductors:
            reason = (_('No dhcp service registered'))
            raise exception.NoValidHost(reason=reason)
        topic = '%s.%s' % (self.topic, conductors[0].hostname.encode('utf-8'))
        return topic

    def provision(self, context, names, target):
        """Change nodes's provision state.

        Synchronously, acquire lock and start the conductor background task
        to change power state of a node.

        :param context: request context.
        :param names: names of nodes.
        :param target: desired power state
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.

        """
        topic = self.get_topic_for()
        cctxt = self.client.prepare(topic=topic or self.topic,
                                    version='1.0')
        return cctxt.call(context, 'provision', names=names,
                              target=target)