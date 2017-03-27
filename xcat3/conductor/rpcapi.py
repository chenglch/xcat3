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
from xcat3.conductor import manager
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
            CONF.api.workers_pool_size)
        self._executor = futurist.GreenThreadPoolExecutor(
            max_workers=CONF.api.workers_pool_size,
            check_and_reject=rejection_func)

    def spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.
        :param func: the function should be called within green thread
        :returns: Future object.
        :raises: NoFreeConductorWorker if worker pool is currently full.

        """
        try:
            future = self._executor.submit(func, *args, **kwargs)
            if kwargs.get('names'):
                setattr(future, 'nodes', kwargs['names'])
        except futurist.RejectedSubmission:
            raise exception.NoFreeAPIWorker()
        return future

    def wait_workers(self, futures, timeout):
        """Wait the complete of multiple future objects

        :param futures: List of future objects.
        :param timout: Max time to wait for the green thread to complete.
        :returns:
            done: A list of future objects finished
            not_done: A list of future objects unfinished

        """
        done, not_done = waiters.wait_for_all(futures, timeout)
        return done, not_done

    def get_topic_for(self, nodes):
        """Get the RPC topic for the conductor service the nodes are mapped to.

        :param nodes: the names of nodes
        :returns: an RPC topic string.
        :raises: NoValidHost

        """
        conductors = self.dbapi.get_conductors()
        if not conductors:
            reason = (_('No conductor service registered'))
            raise exception.NoValidHost(reason=reason)

        topic_dict = dict()
        nodes_list = [[] for i in xrange(len(conductors))]
        per_host = len(nodes) / len(conductors)
        host_id = 0

        for i in xrange(len(nodes)):
            if i == (host_id + 1) * per_host and i != len(nodes) - 1:
                host_id += 1
            nodes_list[host_id].append(nodes[i])

        for i in xrange(len(conductors)):
            topic = '%s.%s' % (self.topic,
                               conductors[i].hostname.encode('utf-8'))
            topic_dict[topic] = nodes_list[i]

        return topic_dict

    def change_power_state(self, context, names, target):
        """Change a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to change power state of a node.

        :param context: request context.
        :param names: names of nodes.
        :param target: desired power state
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.

        """

        def _change_power_state(cctxt, names, target):
            return cctxt.call(context, 'change_power_state', names=names,
                              target=target)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_change_power_state, cctxt, names=nodes,
                                       target=target)
            futures.append(future)

        return futures

    def get_power_state(self, context, names):
        """Get a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to change power state of a node.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        """

        def _get_power_state(cctxt, names):
            return cctxt.call(context, 'get_power_state', names=names)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_get_power_state, cctxt, names=nodes)
            futures.append(future)

        return futures

    def destroy_nodes(self, context, names):
        """Change a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to delete nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.

        """

        def _destroy_nodes(cctxt, names):
            return cctxt.call(context, 'destroy_nodes', names=names)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_destroy_nodes, cctxt, names=nodes)
            futures.append(future)

        return futures

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

        def _provision(cctxt, names, target):
            return cctxt.call(context, 'provision', names=names,
                              target=target)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_provision, cctxt, names=nodes,
                                       target=target)
            futures.append(future)

        return futures

    def get_boot_device(self, context, names):
        """Get a node's boot device

        Synchronously, acquire lock and start the conductor background task
        to get the boot device of nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        """

        def _get_boot_device(cctxt, names):
            return cctxt.call(context, 'get_boot_device', names=names)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_get_boot_device, cctxt, names=nodes)
            futures.append(future)

        return futures

    def set_boot_device(self, context, names, boot_device):
        """Get a node's boot device

        Synchronously, acquire lock and start the conductor background task
        to set the boot device of nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        """

        def _set_boot_device(cctxt, names, boot_device):
            return cctxt.call(context, 'set_boot_device', names=names,
                              boot_device=boot_device)

        topic_dict = self.get_topic_for(names)
        futures = []
        for topic, nodes in topic_dict.items():
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            future = self.spawn_worker(_set_boot_device, cctxt, names=nodes,
                                       boot_device=boot_device)
            futures.append(future)

        return futures
