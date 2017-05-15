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
import six
import traceback
from oslo_log import log
import oslo_messaging as messaging
from futurist import waiters

from xcat3.common import exception
from xcat3.common import utils
from xcat3.conductor import base_manager
from xcat3.conductor import task_manager
from xcat3.conf import CONF
from xcat3.network import dhcp
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
        self.plugins = mapping.PluginMap()

    def _filter_result(self, result, nodes):
        names = [name for name, val in six.iteritems(result) if
                 val == xcat3_states.SUCCESS]
        names_dict = dict((name, True) for name in names)
        nodes = [node for node in nodes if names_dict.has_key(node.name)]
        return names, nodes

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
                # NOTE(chenglch): futurist exception_info returns tuple
                # (exception, traceback). traceback is a object, print the
                # traceback string with traceback module.
                LOG.exception(_LE(
                    'Error in _process_nodes_worker for node %(node)s: '
                    '%(err)s'),
                    {'node': node.name,
                     'err': six.text_type(
                         traceback.print_tb(r.exception_info()[1]))})
                result[node.name] = six.text_type(r.exception())
            else:
                result[node.name] = r.result() if r.result() else \
                    xcat3_states.SUCCESS

        return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def change_power_state(self, context, names, target):
        """RPC method to encapsulate changes to a node's state.

        :param context: an admin context.
        :param names: the names of nodes.
        :param target: the desired power state of the node.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC change_power_state called for nodes %(nodes)s. "
                 "The desired new state is %(target)s.",
                 {'nodes': str(names), 'target': target})

        def _change_power_state(node, target):
            control_plugin = self.plugins.get_control_plugin(node)
            control_plugin.validate(node)
            control_plugin.set_power_state(node, target)

        with task_manager.acquire(context, names, obj_info=['nics', ],
                                  purpose='change power state') as task:
            result = self._process_nodes_worker(_change_power_state,
                                                nodes=task.nodes,
                                                target=target)
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def get_power_state(self, context, names):
        """RPC method to get a node's power state.

        :param context: an admin context.
        :param names: the names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC get_power_state called for nodes %(nodes)s. " %
                 {'nodes': str(names)})

        def _get_power_state(node):
            control_plugin = self.plugins.get_control_plugin(node)
            control_plugin.validate(node)
            return control_plugin.get_power_state(node)

        with task_manager.acquire(context, names, shared=True,
                                  obj_info=['nics', ],
                                  purpose='get power state') as task:
            result = self._process_nodes_worker(_get_power_state,
                                                nodes=task.nodes)
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def destroy_nodes(self, context, names):
        """RPC method to destroy nodes.

        :param context: an admin context.
        :param names: the names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
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
            # remove record about dhcp in database if exist, but do not disable
            # the dhcp service immediately.
            dhcp.ISCDHCPService.update_opts(context, 'remove', names, None)
            # TODO(chenglch): If node is in nodeset state, do not allow this
            # operation as provision data should be clean up at first.
            objects.Node.destroy_nodes(nodes)
            LOG.info(_LI('Successfully deleted nodes %(nodes)s.'),
                     {'nodes': names})

            for node in nodes:
                result[node.name] = xcat3_states.DELETED
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def provision(self, context, names, target, osimage, subnet=None):
        """RPC method to encapsulate changes to a node's state.

        :param context: an admin context.
        :param names: the names of nodes.
        :param target: the desired state of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        def _provision(node, osimage, dhcp_opts, subnet=None):
            """One provision step for each node
            :param node: node to act on
            :param osimage: osimage object, if None means just setup dhcp
                            options.
            :param dhcp_opts: An empty dict used to fill the dhcp options then
                              return to the caller.
            :param subnet: network object.

            """
            boot_plugin = self.plugins.get_boot_plugin(node)
            boot_plugin.validate(node)
            dhcp_opts[node.name].update(boot_plugin.gen_dhcp_opts(node))
            if not osimage:
                node.state = xcat3_states.DEPLOY_DHCP
                return

            node.state = xcat3_states.DEPLOY_NODESET
            node.conductor_affinity = self.service.id
            boot_plugin.nodeset(node, osimage)
            os_plugin = self.plugins.get_osimage_plugin(osimage)
            os_plugin.validate(node)
            os_plugin.render(node, osimage)

        def _clean(node):
            boot_plugin = self.plugins.get_boot_plugin(node)
            boot_plugin.clean(node)
            node.state = xcat3_states.DEPLOY_NONE

        LOG.info("RPC provision called for nodes %(nodes)s. "
                 "The desired new state is %(target)s.",
                 {'nodes': str(names), 'target': target})
        with task_manager.acquire(context, names, obj_info=['nics', ],
                                  purpose='nodes provision') as task:
            dhcp_opts = dict((name, {}) for name in names)
            nodes = task.nodes
            if target and target.startswith('un_'):
                try:
                    # TODO(chenglch): Currently only ISC is supported, use it
                    # directly.
                    dhcp.ISCDHCPService.update_opts(context, 'remove', names,
                                                    None)
                    result = self._process_nodes_worker(_clean, nodes=nodes)
                    objects.Node.update_nodes(nodes)
                except Exception as e:
                    result = dict()
                    utils.fill_result(result, names, e.message)
                return result

            if target == 'dhcp':
                osimage = None

            result = self._process_nodes_worker(_provision,
                                                nodes=nodes,
                                                osimage=osimage,
                                                dhcp_opts=dhcp_opts,
                                                subnet=subnet)
            names, nodes = self._filter_result(result, nodes)
            try:
                dhcp.ISCDHCPService.update_opts(context, 'add', names,
                                                dhcp_opts)
                # update attributes in database
                objects.Node.update_nodes(nodes)
            except Exception as e:
                utils.fill_result(result, names, e.message)

            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def get_boot_device(self, context, names):
        """RPC method to get the boot device of nodes.

        :param context: an admin context.
        :param names: the names of nodes.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC get_boot_device called for nodes %(nodes)s. " %
                 {'nodes': str(names)})

        def _get_boot_device(node):
            control_plugin = self.plugins.get_control_plugin(node)
            control_plugin.validate(node)
            return control_plugin.get_boot_device(node)

        with task_manager.acquire(context, names, shared=True,
                                  obj_info=['nics', ],
                                  purpose='get_boot_device') as task:
            result = self._process_nodes_worker(_get_boot_device,
                                                nodes=task.nodes)
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def set_boot_device(self, context, names, boot_device):
        """RPC method to get the boot device of nodes.

        :param context: an admin context.
        :param names: the names of nodes.
        :param boot_device: the boot device target.
        :raises: NoFreeServiceWorker when there is no free worker to start
                 async task.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue

        """
        LOG.info("RPC set_boot_device boot_device called for nodes "
                 "%(nodes)s. " % {'nodes': str(names),
                                  'boot_device': boot_device})

        def _set_boot_device(node, boot_device):
            control_plugin = self.plugins.get_control_plugin(node)
            control_plugin.validate(node)
            return control_plugin.set_boot_device(node, boot_device)

        with task_manager.acquire(context, names, obj_info=['nics', ],
                                  purpose='set boot device') as task:
            result = self._process_nodes_worker(_set_boot_device,
                                                nodes=task.nodes,
                                                boot_device=boot_device)
            return result

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.NoFreeServiceWorker,
                                   exception.NodeLocked)
    def provision_callback(self, context, name, action):
        """RPC method to continue the provision for node.

        :param context: an admin context.
        :param name: the node name to act on.
        :param action: action message for the node.
        :raises: InvalidParameterValue
        :raises: MissingParameterValue
        """
        LOG.info("RPC provision_callback called for nodes %(nodes)s. " %
                 {'nodes': str(name)})
        with task_manager.acquire(context, [name],
                                  purpose='node provision callback') as task:
            node = task.nodes[0]
            boot_plugin = self.plugins.get_boot_plugin(node)
            boot_plugin.continue_deploy(node)
            node.state = xcat3_states.DEPLOY_DONE
            node.conductor_affinity = None
            objects.Node.update_nodes([node])
