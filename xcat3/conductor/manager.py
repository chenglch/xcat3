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
from xcat3.conductor import base_manager
from xcat3.conductor import task_manager
from xcat3.conf import CONF
from xcat3 import objects
from xcat3.common import states as xcat3_states
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.plugins import mapping

MANAGER_TOPIC = 'xcat3.conductor_manager'

LOG = log.getLogger(__name__)


class ConductorManager(base_manager.BaseConductorManager):
    """XCAT3 Conductor manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(ConductorManager, self).__init__(host, topic)

    def _process_nodes_worker(self, func, nodes, *args, **kwargs):
        """Wait the result from rpc call.
        :param func: the function should be called with green thread
        :param nodes: the list of rpc nodes

        """
        futures = []
        for node in nodes:
            future = self._spawn_worker(func, node=node, *args, **kwargs)
            setattr(future, 'node', node)
            futures.append(future)

        done, not_done = waiters.wait_for_all(futures, CONF.conductor.timeout)
        msg = "Timeout after waiting %(timeout)d seconds" % {
            "timeout": CONF.conductor.timeout}
        result = dict((node.name, msg) for node in nodes)
        for r in done:
            node = getattr(r, 'node')
            if r.exception():
                result[node.name] = r.exception().message
            else:
                result[node.name] = r.result() if r.result() else \
                    xcat3_states.SUCCESS

        return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeConductorWorker,
                                   exception.NodeLocked)
    def change_power_state(self, context, names, target):
        """RPC method to encapsulate changes to a node's state.

        :param context: an admin context.
        :param names: the names of nodes.
        :param target: the desired power state of the node.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC change_power_state called for nodes %(nodes)s. "
                 "The desired new state is %(target)s.",
                 {'nodes': str(names), 'target': target})

        def _change_power_state(node, target):
            control_plugin, os_plugin, boot_plugin = mapping.get_plugin(node)
            control_plugin.set_power_state(node, target)

        with task_manager.acquire(context, names,
                                  purpose='nodes deletion') as task:
            result = self._process_nodes_worker(_change_power_state,
                                                nodes=task.nodes,
                                                target=target)
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeConductorWorker,
                                   exception.NodeLocked)
    def destroy_nodes(self, context, names):
        """RPC method to destroy nodes.

        :param context: an admin context.
        :param names: the names of nodes.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC destroy_nodes called for nodes %(nodes)s. ",
                 {'nodes': str(names)})
        result = dict()
        with task_manager.acquire(context, names,
                                  purpose='nodes deletion') as task:
            nodes = task.nodes
            objects.Node.destroy_nodes(nodes)
            LOG.info(_LI('Successfully deleted nodes %(nodes)s.'),
                     {'nodes': names})

            for node in nodes:
                result[node.name] = xcat3_states.DELETED
            return result
