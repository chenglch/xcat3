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

import datetime
import pecan
from oslo_log import log
from pecan import rest
from xcat3.api import expose
from xcat3.db import api as db_api
import xcat3.conf
import six
from six.moves import http_client
import retrying
import traceback
from xcat3.common import exception
from xcat3.common import utils
from xcat3.common import states
from xcat3.api.controllers.v1 import types
import wsme
from wsme import types as wtypes
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.api.controllers import base
from xcat3.api.controllers import link
from xcat3.api.controllers.v1 import collection
from xcat3.api.controllers.v1 import utils as api_utils
from xcat3.common import states as xcat3_states
from xcat3 import objects

CONF = xcat3.conf.CONF

LOG = log.getLogger(__name__)

_DEFAULT_RETURN_FIELDS = ('name', 'reservation', 'created_at', 'nics_info',
                          'state', 'task_action', 'type', 'arch', 'mgt',
                          'updated_at', 'id')
_UNSET_NODE_FIELDS = ('id', 'created_at', 'updated_at')
_REST_RESOURCE = ('power', 'provision', 'boot_device')

ALLOWED_TARGET_POWER_STATES = (xcat3_states.POWER_ON,
                               xcat3_states.POWER_OFF)

dbapi = db_api.get_instance()


def _wait_rpc_result(futures, names, result, json=True):
    """Wait the result from rpc call.

    :param futures: api worker objects
    :param nodes: node list for rpc request
    :param result: node dict for the result
    :param json: if True, the the result will be send back through rest api,
                 if it is just intermediate value, set False
    :return: json type result,
    """
    done, not_done = pecan.request.rpcapi.wait_workers(futures,
                                                       CONF.api.timeout)
    for r in done:
        nodes = getattr(r, 'nodes', None)
        if r.exception():
            LOG.exception(_LE('Error in wait_workers %(err)s'),
                          {'err': six.text_type(r.exception())})
            if nodes:
                utils.fill_result(result['nodes'], nodes,
                                  r.exception().message)
            else:
                result['error'] = r.exception().message
            if hasattr(r.exception(), 'code'):
                result['errorcode'] = r.exception().code
        else:
            # Manager should return a dict result
            utils.fill_dict_result(result['nodes'], r.result())

    msg = "Timeout after waiting %(timeout)d seconds" % {
        "timeout": CONF.api.timeout}
    for r in not_done:
        nodes = getattr(r, 'nodes', None)
        utils.fill_result(result['nodes'], nodes, msg)

    return types.JsonType.validate(result) if json else result


def _filter_unavailable_nodes(names, share=False):
    """Exclude the non-exist nodes or locked nodes.

        :param names: nodes names
        :return: json type result, list of nodes names
    """

    result = dict()
    msg = _("Could not be found.")
    # For the performance consideration, use dbapi directly
    exist_names = dbapi.get_node_in(names, fields=['name', ])
    exist_names = [name[0] for name in exist_names]
    result['nodes'] = dict(
        (name, msg) for name in names if name not in exist_names)
    names = exist_names
    if not share:
        msg = _("Locked temporarily")
        locked_names = dbapi.get_node_in(names, filters=['not_reservation', ],
                                         fields=['name', ])
        locked_names = [name[0] for name in locked_names]
        for name in locked_names:
            result['nodes'][name] = msg
        names = filter(lambda n: n not in locked_names, names)
    return result, names


class Node(base.APIBase):
    """API representation of a bare metal node.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a node.
    """
    id = wsme.wsattr(int, readonly=True)
    name = wsme.wsattr(wtypes.text, mandatory=True)
    """The logical name for this node"""
    reservation = wsme.wsattr(wtypes.text, readonly=True)
    """The hostname of the conductor that holds an exclusive lock on
    the node."""
    mgt = wsme.wsattr(wtypes.text)
    netboot = wsme.wsattr(wtypes.text)
    type = wsme.wsattr(wtypes.text)
    arch = wsme.wsattr(wtypes.text)
    state = wsme.wsattr(wtypes.text)
    osimage_name = wsme.wsattr(wtypes.text)
    scripts_name = wsme.wsattr(wtypes.text)
    control_info = {wtypes.text: types.jsontype}
    console_info = {wtypes.text: types.jsontype}
    nics_info = {wtypes.text: types.jsontype}
    conductor_affinity = workers = wsme.wsattr(int, readonly=True)
    osimage_id = wsme.wsattr(int, readonly=True)
    passwd_id = wsme.wsattr(int, readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Node.fields)
        for k in fields:
            # Add fields we expose.
            if hasattr(self, k):
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def convert_with_links(node, fields=None):
        node = Node(**node.as_dict())
        node.filter_fields(fields, _UNSET_NODE_FIELDS)
        return node

    @classmethod
    def sample(cls, expand=True):
        time = datetime.datetime(2000, 1, 1, 12, 0, 0)
        name = 'database16-dc02'
        sample = cls(name=name,
                     last_error=None,
                     updated_at=time,
                     created_at=time,
                     reservation=None)
        fields = None if expand else _DEFAULT_RETURN_FIELDS
        return cls.convert_with_links(sample, fields=fields)

    @classmethod
    def get_api_node(cls, node_name):
        return cls(name=node_name)


class NodePatchType(types.JsonPatchType):
    _api_base = Node

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults


class NodeCollection(collection.Collection):
    """API representation of a collection of nodes."""

    nodes = [Node]
    """A list containing nodes objects"""

    def __init__(self, *args, **kwargs):
        self._type = 'nodes'

    @staticmethod
    def convert_with_links(nodes, limit=50, url=None, fields=None, **kwargs):
        collection = NodeCollection()
        if fields and len(fields) == 1 and 'nics' in fields:
            fields = None
        elif 'nics' in fields:
            fields.remove('nics')
            fields.append('nics_info')
        collection.nodes = [Node.convert_with_links(n, fields=fields)
                            for n in nodes]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        node = Node.sample(expand=False)
        sample.nodes = [node]
        return sample


class NodeProvisionController(rest.RestController):

    _custom_actions = {
        'callback': ['PUT']
    }

    @expose.expose(types.jsontype, wtypes.text,
                   wtypes.text, wtypes.text,
                   body=NodeCollection,
                   status_code=http_client.ACCEPTED)
    def put(self, target, osimage=None, subnet=None, nodes=None):
        """Set the provision state of the nodes.

        :param target: The desired state of the node.
        :param osimage: The osimage to deploy.
        :param subnet: the subnet used for deploying
        :param nodes: the name of nodes.
        :raises: ClientSideError (HTTP 409) if a provision operation is
                 already in progress.
        :raises: InvalidStateRequested (HTTP 400) if the requested target
                 state is not valid or if the node is in CLEANING state.
        :raises: NotAcceptable (HTTP 406) the target state is not supported.
        :raises: Invalid (HTTP 400) if timeout value is less than 1.

        """
        names = [node.name for node in nodes.nodes if node.name]
        if not names:
            raise exception.InvalidParameterValue(
                _("The node %(node)s is invalid") % {'node': nodes})
        result, names = _filter_unavailable_nodes(names)
        if not names:
            return result
        context = pecan.request.context
        # Get the rpc object which can transfer via rpc calls
        if subnet:
            subnet = objects.Network.get_by_name(context, subnet)
        if osimage:
            osimage = objects.OSImage.get_by_name(context, osimage)

        if not target.startswith('un_'):
            futures = pecan.request.rpcapi.provision(context, names,
                                                     target=target,
                                                     osimage=osimage,
                                                     subnet=subnet)
        else:
            futures = pecan.request.rpcapi.clean(context, result, names)

        result = _wait_rpc_result(futures, names, result, False)
        try:
            # As rpc result from conductor nodes has came back, the async calls
            # should be accepted by the network service node. Here, we build
            # dhcp options for all the split parts together.
            pecan.request.network_api.enable_dhcp_option(context, subnet)
        except Exception as e:
            LOG.exception(_LE(
                'Unexpected exception while activating dhcp service '
                '%(err)s'), {'err': six.text_type(traceback.format_exc())})
            utils.fill_result(result['nodes'], names, e.message)

        return types.JsonType.validate(result)


    @expose.expose(types.jsontype, wtypes.text, body=types.jsontype)
    def callback(self, name, action=None):
        msg = "Callback request reveived name=%(name)s" % {'name':name}
        if action is not None:
            msg += ' action=%s' % str(action)
        LOG.info(_LI(msg))
        node = objects.Node.get_by_name(pecan.request.context, name)
        if node.state != xcat3_states.DEPLOY_NODESET or \
                        node.conductor_affinity is None:
            raise exception.DeployStateFailure(name=node.name)
        if action is not None:
            if action.has_key('fetch_ssh_pub'):
                key = {'pub_key': None}
                with open('/root/.ssh/id_rsa.pub', 'r') as f:
                    key['pub_key'] = f.read()
                    return types.JsonType.validate(key)

        topic = pecan.request.rpcapi.get_topic_for_callback(
            node.conductor_affinity)
        pecan.request.rpcapi.provision_callback(pecan.request.context, name,
                                                action, topic)


class BootDeviceController(rest.RestController):
    @expose.expose(types.jsontype, wtypes.text, body=NodeCollection,
                   status_code=http_client.ACCEPTED)
    def put(self, target, nodes):
        """Set the boot device for nodes.

        Set the boot device to use on next reboot of the nodes.

        :param nodes: list of nodes
        :param boot_device: the boot device.
        :returns: json format about the status of nodes
        """
        names = [node.name for node in nodes.nodes if node.name]
        result, names = _filter_unavailable_nodes(names)
        futures = pecan.request.rpcapi.set_boot_device(
            pecan.request.context, names, target)
        result = _wait_rpc_result(futures, names, result)
        return result

    @expose.expose(types.jsontype, body=NodeCollection)
    def get(self, nodes):
        """Get the current boot device for a node.

        :param nodes: list of node to check
        :returns: json format about the status of nodes
        """
        names = [node.name for node in nodes.nodes if node.name]
        result, names = _filter_unavailable_nodes(names)
        futures = pecan.request.rpcapi.get_boot_device(
            pecan.request.context, names)
        result = _wait_rpc_result(futures, names, result)
        return result


class NodePowerController(rest.RestController):
    @expose.expose(types.jsontype, body=NodeCollection)
    def get(self, nodes):
        """List the states of the node.

        :param node_name: The name of a node.
        """
        names = [node.name for node in nodes.nodes if node.name]
        result, names = _filter_unavailable_nodes(names)
        futures = pecan.request.rpcapi.get_power_state(
            pecan.request.context, names)
        result = _wait_rpc_result(futures, names, result)
        return result

    @expose.expose(types.jsontype, wtypes.text,
                   wtypes.text,
                   body=NodeCollection,
                   status_code=http_client.ACCEPTED)
    def put(self, target, nodes):
        """Set the power state of the node.

        :param target: The desired power state of the node.
        :param nodes: the name of nodes.
        :raises: ClientSideError (HTTP 409) if a power operation is
                 already in progress.
        :raises: InvalidStateRequested (HTTP 400) if the requested target
                 state is not valid or if the node is in CLEANING state.
        :raises: NotAcceptable (HTTP 406) for soft reboot, soft power off or
          timeout parameter, if requested version of the API is less than 1.27.
        :raises: Invalid (HTTP 400) if timeout value is less than 1.

        """
        names = [node.name for node in nodes.nodes if node.name]
        result, names = _filter_unavailable_nodes(names)
        futures = pecan.request.rpcapi.change_power_state(
            pecan.request.context, names, target=target)
        result = _wait_rpc_result(futures, names, result)
        url_args = '/'.join('states')
        pecan.response.location = link.build_url('nodes', url_args)
        return result


class NodesController(rest.RestController):
    power = NodePowerController()
    provision = NodeProvisionController()
    boot_device = BootDeviceController()
    invalid_sort_key_list = ['console_info', 'control_info', 'nics']

    _custom_actions = {
        'info': ['GET']
    }

    def _check_names_acceptable(self, names, error_msg):
        """Checks all node 'name's are acceptable, it does not return a value.

        This function will raise an exception for unacceptable names.

        :param names: list of node names to check
        :param error_msg: error message in case of wsme.exc.ClientSideError,
            should contain %(name)s placeholder.
        :raises: wsme.exc.ClientSideError
        """
        for name in names:
            if not api_utils.is_valid_node_name(name):
                raise wsme.exc.ClientSideError(
                    error_msg % {'name': name},
                    status_code=http_client.BAD_REQUEST)

    def _delete(self, node):
        node_obj = api_utils.get_node_obj(node)
        node_obj.destroy()

    def _get_nodes_collection(self, names, limit=None, sort_key='id',
                              sort_dir='asc', fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})

        nodes = objects.Node.list_in(pecan.request.context, names,
                                     obj_info=fields)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        return NodeCollection.convert_with_links(nodes, limit,
                                                 fields=fields,
                                                 **parameters)

    def _update_changed_fields(self, node, node_obj):
        """Update rpc_node based on changed fields in a node.

        """
        for field in objects.Node.fields:
            try:
                patch_val = getattr(node, field)
            except AttributeError:
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if node_obj[field] != patch_val:
                node_obj[field] = patch_val

    @expose.expose(NodeCollection, types.listtype, body=NodeCollection)
    def info(self, fields=None, nodes=None):
        if not fields:
            fields = ['nics', ]
        names = [node.name for node in nodes.nodes if node.name]
        return self._get_nodes_collection(names, limit=None, fields=fields)

    @expose.expose(Node, types.name, types.listtype)
    def get_one(self, node_name, fields=None):
        node = Node.get_api_node(node_name)
        node_obj = api_utils.get_node_obj(node)
        return Node.convert_with_links(node_obj, fields=fields)

    @expose.expose(types.jsontype, int, wtypes.text, wtypes.text, wtypes.text,
                   types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of nodes.

        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the xcat3 configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        fields = ['name', ]
        # TODO(chenglch): limit is not supported very well
        db_nodes = dbapi.get_node_list(limit=limit, sort_key=sort_key,
                                       sort_dir=sort_dir, fields=fields)
        results = {'nodes': []}
        results['nodes'] = [node[0] for node in db_nodes]
        return results

    @expose.expose(types.jsontype, body=NodeCollection,
                   status_code=http_client.CREATED)
    def post(self, nodes):
        """Create nodes

        :param nodes: Nodes with the request
        """

        def _create_object(node, result):
            new_node = None
            try:
                context = pecan.request.context
                if node.name in _REST_RESOURCE:
                    raise exception.InvalidName(name=node.name)
                new_node = objects.Node(context, **node.as_dict())
            except Exception as e:
                result['nodes'][node.name] = e.message
            else:
                result['nodes'][node.name] = states.SUCCESS
            return new_node

        def singal_create(nodes, result):
            """Create node one by one

            :param nodes: the api nodes
            :param result: a dict contains the return result
            :return: json type result
            """
            for node in nodes:
                new_node = _create_object(node, result)
                try:
                    new_node.create()
                except Exception as e:
                    result['nodes'][node.name] = e.message
                else:
                    result['nodes'][node.name] = states.SUCCESS
            return result

        def bulk_create(nodes, result):
            """Create nodes in bulk mode

            :param nodes: the api nodes
            :param result: a dict contains the return result
            :return: json type result
            """
            names = [node.name for node in nodes]
            exist_names = dbapi.get_node_list(names, fields=['name', ])
            exist_names = [name[0] for name in exist_names]
            dups = utils.get_duplicate_list(names + exist_names)
            msg = _("Error: duplicate name")
            for item in dups:
                result['nodes'][item] = msg
            nodes = filter(lambda x: x.name not in dups, nodes)
            new_nodes = [_create_object(node, result) for node in nodes if
                         node is not None]
            if new_nodes:
                objects.Node.create_nodes(new_nodes)
            return result

        result = dict()
        result['nodes'] = dict()
        nodes = nodes.nodes
        # 15 can be any number else
        if len(nodes) < 15:
            result = singal_create(nodes, result)
        else:
            result = bulk_create(nodes, result)
        return types.JsonType.validate(result)

    @expose.expose(types.jsontype, body=NodeCollection,
                   status_code=http_client.ACCEPTED)
    def delete(self, nodes):
        """Delete nodes

        Dispatch the request to multiple conductors to perform the delete
        action.

        :param nodes: nodes to delete, api format
        :return: json fomat result
        """

        names = [node.name for node in nodes.nodes if node.name]
        result, names = _filter_unavailable_nodes(names)
        if not names:
            return types.JsonType.validate(result)
        # As node may be used by other request, try to acquire lock then
        # delete nodes
        futures = pecan.request.rpcapi.destroy_nodes(
            pecan.request.context, names)

        result = _wait_rpc_result(futures, names, result)
        return types.JsonType.validate(result)

    @expose.expose(types.jsontype, body=types.jsontype)
    def patch(self, patch_dict):
        """Update an existing node.

        :param node_name: The name of a node.
        :param patch: a json PATCH document to apply to this node.
        :return: json format api node
        """
        nodes = patch_dict['nodes']
        patches = patch_dict['patches']

        for patch in patches:
            patch = NodePatchType(**patch)

        names = [node['name'] for node in nodes if node.has_key('name')]
        result, names = _filter_unavailable_nodes(names, share=True)
        try:
            objs = objects.Node.list_in(pecan.request.context, names)
            new_objs = []
            for obj in objs:
                api_obj = Node(
                    **api_utils.apply_jsonpatch(obj.as_dict(), patches))
                self._update_changed_fields(api_obj, obj)
                new_objs.append(obj)
            objects.Node.update_nodes(new_objs)
            for name in names:
                result['nodes'][name] = states.UPDATED
        except Exception() as e:
            for name in names:
                result['nodes'][name] = e.message

        return result
