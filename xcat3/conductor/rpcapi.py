# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
"""
Client side of the conductor RPC API.
"""

import futurist
from futurist import rejection
from futurist import waiters
from oslo_log import log
import oslo_messaging as messaging
import six

from xcat3.common import exception
from xcat3.common import rpc
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.conf import CONF
from xcat3.db import api as dbapi
from xcat3.objects import base as objects_base

LOG = log.getLogger(__name__)
MANAGER_TOPIC = 'xcat3.conductor_manager'

class ConductorAPI(object):
    """Client side of the conductor RPC API.
    """
    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(ConductorAPI, self).__init__()
        self.topic = topic
        self.dbapi = dbapi.get_instance()
        if self.topic is None:
            self.topic = MANAGER_TOPIC

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
        :raises: NoFreeServiceWorker if worker pool is currently full.

        """

        def _worker(futures, func, *args, **kwargs):
            try:
                future = self._executor.submit(func, *args, **kwargs)
                if kwargs.get('names'):
                    setattr(future, 'nodes', kwargs['names'])
                futures.append(future)
            except futurist.RejectedSubmission:
                raise exception.NoFreeAPIWorker()

        futures = []
        local_workers = kwargs.pop('workers')
        if local_workers > 1 and kwargs.get('names') and len(
                kwargs.get('names')) < CONF.api.per_group_count:
            local_workers = 1

        if local_workers > 1:
            names = kwargs.pop('names')
            groups = [[] for i in range(local_workers)]
            per_group = len(names) / local_workers
            for i in range(local_workers - 1):
                groups[i].extend(names[i * per_group:(i + 1) * per_group])
            groups[local_workers - 1].extend(
                names[(local_workers - 1) * per_group:])
            for i in range(local_workers):
                kwargs['names'] = groups[i]
                if not kwargs['names']:
                    continue
                _worker(futures, func, *args, **kwargs)
        elif kwargs['names']:
            _worker(futures, func, *args, **kwargs)
        return futures

    def wait_workers(self, futures, timeout):
        """Wait the complete of multiple future objects

        :param futures: List of future objects.
        :param timout: Max time to wait for the green thread to complete.
        :returns: (done, not_done) pair
            done: A list of future objects finished
            not_done: A list of future objects unfinished
        """
        return waiters.wait_for_all(futures, timeout)

    def get_topic_for(self, nodes):
        """Get the RPC topic for the conductor service the nodes are mapped to.

        This function is for rpc calls for multiple nodes.

        :param nodes: the names of nodes
        :returns: an RPC topic string.
        :raises: NoValidHost

        """
        conductors = self.dbapi.get_services(type='conductor')
        if not conductors:
            reason = (_('No conductor service registered'))
            raise exception.NoValidHost(reason=reason)

        topic_dict = dict()
        workers = 0
        for cond in conductors:
            # rpc workers is the number of child processes
            cond.workers = cond.workers + 1 if cond.workers > 1 else 1
            workers += cond.workers

        per_worker = len(nodes) / workers
        j = 0
        for i in range(len(conductors) - 1):
            cond = conductors[i]
            topic = '%s.%s' % (self.topic, cond.hostname.encode('utf-8'))
            t = dict()
            t['nodes'] = nodes[j: cond.workers * per_worker]
            t['workers'] = cond.workers
            topic_dict[topic] = t
            j += cond.workers * per_worker

        cond = conductors[len(conductors) - 1]
        topic = '%s.%s' % (self.topic, cond.hostname.encode('utf-8'))
        t = {'nodes': nodes[j:], 'workers': cond.workers}
        topic_dict[topic] = t
        return topic_dict

    def get_topic_for_callback(self, conductor_id):
        """Get rpc topic for callback node

        :param node: the callback node
        """
        conductor = self.dbapi.get_service_from_id(id=conductor_id)
        if not conductor:
            reason = (_('Conductor %(id)s is not registered') % conductor_id)
            raise exception.NoValidHost(reason=reason)
        return '%s.%s' % (self.topic, conductor.hostname.encode('utf-8'))

    def get_topic_for_affinity(self, names, result):
        # nodes [('<node_name>', affinity_id),]
        nodes = self.dbapi.get_node_affinity_in(names)
        conductors = self.dbapi.get_services(type='conductor')
        if not conductors:
            reason = (_('No conductor service registered'))
            raise exception.NoValidHost(reason=reason)
        cond_dict = dict((c.id, '%s.%s' % (self.topic,
            c.hostname.encode('utf-8'))) for c in conductors)
        topic_dict = dict(('%s.%s' % (self.topic, c.hostname.encode('utf-8')),
                           {'nodes': [], 'workers': c.workers}) for c in
                          conductors)
        default_topic = '%s.%s' % (self.topic,
                                   conductors[0].hostname.encode('utf-8'))
        for node in nodes:
            if node[1]:
                if cond_dict.has_key(node[1]):
                    topic = cond_dict[node[1]]
                else:
                    result['nodes'][node[0]] = _(
                        "Conductor %s could not be found" % node[1])
                    continue
            else:
                topic = default_topic
            topic_dict[topic]['nodes'].append(node[0])
        return topic_dict

    def spawn_rpc_worker(self, func, *args, **kwargs):
        """Start greensthread for every conductor host

        :param func: function to run in the greenthread
        :param affinity: boolean value indicate whether to run rpc request on
                         specific host
        :return result:  result dict contains the return status for each node
        :raises: InvalidParameterValue
        """
        if not kwargs.has_key('names'):
            raise exception.InvalidParameterValue(
                _("Invalid parameter kwargs %(kwargs)s") % {
                    'kwargs': str(kwargs)})
        topic_dict = self.get_topic_for(kwargs.pop('names'))

        futures = []
        for topic, node_info in topic_dict.items():
            nodes = node_info['nodes']
            workers = node_info['workers']
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            temp = self.spawn_worker(func, cctxt, workers=workers, names=nodes,
                                     *args, **kwargs)
            futures.extend(temp)

        return futures

    def spawn_affinity_worker(self, result, func, *args, **kwargs):
        """Start greensthread for every conductor host

        :param func: function to run in the greenthread
        :param affinity: boolean value indicate whether to run rpc request on
                         specific host
        :return result:  result dict contains the return status for each node
        :raises: InvalidParameterValue
        """
        if not kwargs.has_key('names'):
            raise exception.InvalidParameterValue(
                _("Invalid parameter kwargs %(kwargs)s") % {
                    'kwargs': str(kwargs)})

        topic_dict = self.get_topic_for_affinity(kwargs.pop('names'), result)
        futures = []
        for topic, node_info in topic_dict.items():
            nodes = node_info['nodes']
            workers = node_info['workers']
            cctxt = self.client.prepare(topic=topic or self.topic,
                                        version='1.0')
            temp = self.spawn_worker(func, cctxt, workers=workers, names=nodes,
                                     *args, **kwargs)
            futures.extend(temp)

        return futures

    def change_power_state(self, context, names, target):
        """Change a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to change power state of a node.

        :param context: request context.
        :param names: names of nodes.
        :param target: desired power state
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.

        """

        def _change_power_state(cctxt, names, target):
            return cctxt.call(context, 'change_power_state', names=names,
                              target=target)

        return self.spawn_rpc_worker(_change_power_state, names=names,
                                     target=target)

    def get_power_state(self, context, names):
        """Get a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to change power state of a node.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """

        def _get_power_state(cctxt, names):
            return cctxt.call(context, 'get_power_state', names=names)

        return self.spawn_rpc_worker(_get_power_state, names=names)

    def destroy_nodes(self, context, names):
        """Change a node's power state.

        Synchronously, acquire lock and start the conductor background task
        to delete nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.

        """

        def _destroy_nodes(cctxt, names):
            return cctxt.call(context, 'destroy_nodes', names=names)

        return self.spawn_rpc_worker(_destroy_nodes, names=names)

    def provision(self, context, names, target, osimage, subnet=None):
        """Change nodes's provision state.

        Synchronously, acquire lock and start the conductor background task
        to deploy nodes.

        :param context: request context.
        :param names: names of nodes.
        :param target: desired power state
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """

        def _provision(cctxt, names, target, osimage, subnet=None):
            return cctxt.call(context, 'provision', names=names,
                              target=target, osimage=osimage, subnet=subnet)

        return self.spawn_rpc_worker(_provision, names=names, target=target,
                                     osimage=osimage, subnet=subnet)

    def clean(self, context, result, names):
        """Clean up the files and configuration while depoying.

        Synchronously, acquire lock and start the conductor background task
        to clean the env.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """
        def _clean(cctxt, names):
            return cctxt.call(context, 'clean', names=names)

        self.dbapi.destroy_dhcp(names)
        return self.spawn_affinity_worker(result, _clean, names=names)

    def get_boot_device(self, context, names):
        """Get a node's boot device

        Synchronously, acquire lock and start the conductor background task
        to get the boot device of nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """

        def _get_boot_device(cctxt, names):
            return cctxt.call(context, 'get_boot_device', names=names)

        return self.spawn_rpc_worker(_get_boot_device, names=names)

    def set_boot_device(self, context, names, boot_device):
        """Get a node's boot device

        Synchronously, acquire lock and start the conductor background task
        to set the boot device of nodes.

        :param context: request context.
        :param names: names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """

        def _set_boot_device(cctxt, names, boot_device):
            return cctxt.call(context, 'set_boot_device', names=names,
                              boot_device=boot_device)

        return self.spawn_rpc_worker(_set_boot_device, names=names,
                                     boot_device=boot_device)

    def provision_callback(self, context, name, action, topic):
        """RPC method to continue the provision for node.

        :param context: an admin context.
        :param name: the node name to act on.
        :param action: action message for the node.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        cctxt.cast(context, 'provision_callback', name=name, action=action)
