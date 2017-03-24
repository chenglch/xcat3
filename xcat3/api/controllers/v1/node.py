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

import datetime

import pecan
from oslo_log import log
from pecan import rest
from xcat3.api import expose
import xcat3.conf
from six.moves import http_client
from xcat3.common import exception
from xcat3.api.controllers.v1 import types
import wsme
from wsme import types as wtypes

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
                          'updated_at')

_REST_RESOURCE = ('power')

ALLOWED_TARGET_POWER_STATES = (xcat3_states.POWER_ON,
                               xcat3_states.POWER_OFF,
                               xcat3_states.REBOOT,
                               xcat3_states.SOFT_REBOOT,
                               xcat3_states.SOFT_POWER_OFF)


def _bulk_local_wrap(func, nodes, *args, **kwargs):
    """Call the function for each node one by one

    :param func: the function called for each node
    :param nodes: a list of API nodes
    :return: json type result
    """
    result = dict()
    result['nodes'] = dict()
    result['success'] = 0
    result['error'] = 0
    nodes = nodes.nodes
    for node in nodes:
        node_name = api_utils.get_node_name(node)
        try:
            func(node)
        except Exception as e:
            result['nodes'][node_name] = e.message
            result['error'] += 1
        else:
            result['success'] += 1
            result['nodes'][node_name] = 'ok'
    return types.JsonType.validate(result)


def _wait_rpc_result(futures, names):
    """Wait the result from rpc call.


    :param futures: api worker objects
    :param nodes: node list for rpc request
    :return: json type result
    """
    done, not_done = pecan.request.rpcapi.wait_workers(futures,
                                                       CONF.api.timeout)
    msg = "Timeout after waiting %(timeout)d seconds" % {
        "timeout": CONF.api.timeout}
    result = dict()
    result['nodes'] = dict((name, msg) for name in names)
    for r in done:
        nodes = getattr(r, 'nodes', None)
        if r.exception():
            if nodes:
                for node in nodes:
                    result['nodes'][node] = r.exception().message
            else:
                result['error'] = r.exception().message
            result['errorcode'] = r.exception().code
        else:
            # Manager should return a dict result
            for k, v in r.result().items():
                result['nodes'][k] = v

    return types.JsonType.validate(result)


class Node(base.APIBase):
    """API representation of a bare metal node.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a node.
    """
    name = wsme.wsattr(wtypes.text)
    """The logical name for this node"""
    reservation = wsme.wsattr(wtypes.text, readonly=True)
    """The hostname of the conductor that holds an exclusive lock on
    the node."""
    mgt = wsme.wsattr(wtypes.text)
    type = wsme.wsattr(wtypes.text)
    arch = wsme.wsattr(wtypes.text)
    osimage_name = wsme.wsattr(wtypes.text)
    scripts_name = wsme.wsattr(wtypes.text)
    control_info = {wtypes.text: types.jsontype}
    console_info = {wtypes.text: types.jsontype}
    nics_info = {wtypes.text: types.jsontype}

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
        node_name = node.name
        if fields is not None:
            node.unset_fields_except(fields)

        node.ports = [link.Link.make_link('self', pecan.request.public_url,
                                          'nodes',
                                          node_name + "/nics"),
                      link.Link.make_link('bookmark', pecan.request.public_url,
                                          'nodes',
                                          node_name + "/nics",
                                          bookmark=True)
                      ]

        node.links = [link.Link.make_link('self',
                                          pecan.request.public_url,
                                          'nodes',
                                          node_name),
                      link.Link.make_link('bookmark',
                                          pecan.request.public_url,
                                          'nodes',
                                          node_name,
                                          bookmark=True)
                      ]
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


class NodeStates(base.APIBase):
    """API representation of the states of a node."""

    power_state = wtypes.text
    """Represent the current (not transition) power state of the node"""

    task_action = wtypes.text
    """Represent the current (not transition) task action of the node"""

    state = wtypes.text
    """Represent the current (not transition) state of the node"""

    last_error = wtypes.text
    """Any error from the most recent (last) asynchronous transaction that
    started but failed to finish."""

    @staticmethod
    def convert(node_obj):
        attr_list = ['last_error', 'power_state', 'task_action']
        states = NodeStates()
        for attr in attr_list:
            setattr(states, attr, getattr(node_obj, attr))
        return states

    @classmethod
    def sample(cls):
        sample = cls(last_error=None,
                     action=None,
                     power_state=xcat3_states.POWER_ON,
                     state=None)
        return sample


class NodePowerController(rest.RestController):

    @expose.expose(types.jsontype, body=NodeCollection)
    def get(self, nodes):
        """List the states of the node.

        :param node_name: The name of a node.
        """
        names = [node.name for node in nodes.nodes if node.name]
        futures = pecan.request.rpcapi.get_power_state(
            pecan.request.context, names)
        result = _wait_rpc_result(futures, names)
        return result

    @expose.expose(types.jsontype, wtypes.text,
                   wtypes.text,
                   body=NodeCollection,
                   status_code=http_client.ACCEPTED)
    def put(self, target, nodes):
        """Set the power state of the node.

        :param target: The desired power state of the node.
        :param nodes: the UUID or logical name of nodes.
        :raises: ClientSideError (HTTP 409) if a power operation is
                 already in progress.
        :raises: InvalidStateRequested (HTTP 400) if the requested target
                 state is not valid or if the node is in CLEANING state.
        :raises: NotAcceptable (HTTP 406) for soft reboot, soft power off or
          timeout parameter, if requested version of the API is less than 1.27.
        :raises: Invalid (HTTP 400) if timeout value is less than 1.

        """
        # node = Node.get_api_node(node_ident)
        # node_obj = api_utils.get_node_obj(node)
        if (target in [xcat3_states.SOFT_REBOOT, xcat3_states.SOFT_POWER_OFF]):
            raise exception.NotAcceptable()
        names = [node.name for node in nodes.nodes if node.name]

        futures = pecan.request.rpcapi.change_power_state(
            pecan.request.context, names, target=target)
        result = _wait_rpc_result(futures, names)
        url_args = '/'.join('states')
        pecan.response.location = link.build_url('nodes', url_args)
        return result


class NodesController(rest.RestController):
    power = NodePowerController()
    invalid_sort_key_list = ['name']

    def _check_names_acceptable(self, names, error_msg):
        """Checks all node 'name's are acceptable, it does not return a value.

        This function will raise an exception for unacceptable names.

        :param names: list of node names to check
        :param error_msg: error message in case of wsme.exc.ClientSideError,
            should contain %(name)s placeholder.
        :raises: exception.NotAcceptable
        :raises: wsme.exc.ClientSideError
        """
        if not api_utils.allow_node_logical_names():
            raise exception.NotAcceptable()

        for name in names:
            if not api_utils.is_valid_node_name(name):
                raise wsme.exc.ClientSideError(
                    error_msg % {'name': name},
                    status_code=http_client.BAD_REQUEST)

    def _create(self, node):
        context = pecan.request.context
        if node.name in _REST_RESOURCE:
            raise exception.InvalidName(name=node.name)
        new_node = objects.Node(context, **node.as_dict())
        new_node.create()

    def _delete(self, node):
        node_obj = api_utils.get_node_obj(node)
        node_obj.destroy()

    def _get_nodes_collection(self, limit=1000, sort_key='id', sort_dir='asc',
                              fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})
        filters = {}
        nodes = objects.Node.list(pecan.request.context, limit,
                                  sort_key=sort_key, sort_dir=sort_dir,
                                  filters=filters, fields=None)

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

    @expose.expose(Node, types.name, types.listtype)
    def get_one(self, node_name, fields=None):
        node = Node.get_api_node(node_name)
        node_obj = api_utils.get_node_obj(node)
        return Node.convert_with_links(node_obj, fields=fields)

    @expose.expose(NodeCollection, int, wtypes.text, wtypes.text, wtypes.text,
                   types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc',
                fields=None):
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
        if fields is None:
            fields = ['name']
        return self._get_nodes_collection(limit, sort_key, sort_dir,
                                          fields=fields)

    @expose.expose(types.jsontype, body=NodeCollection,
                   status_code=http_client.CREATED)
    def post(self, nodes):
        """Create nodes

        :param nodes: Nodes with the request
        """
        return _bulk_local_wrap(self._create, nodes)

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
        # As node may be used by other request, try to acquire lock then
        # delete nodes
        futures = pecan.request.rpcapi.destroy_nodes(
            pecan.request.context, names)

        result = _wait_rpc_result(futures, names)
        return types.JsonType.validate(result)

    @expose.expose(Node, types.name, body=[NodePatchType])
    def patch(self, node_name, patch):
        """Update an existing node.

        :param node_name: The name of a node.
        :param patch: a json PATCH document to apply to this node.
        :return: json format api node
        """
        node = Node.get_api_node(node_name)
        node_obj = api_utils.get_node_obj(node)
        names = api_utils.get_patch_values(patch, '/name')
        if len(names):
            error_msg = (_("Node %s: Cannot change name to invalid name ")
                         % node_name)
            error_msg += "'%(name)s'"
            self._check_names_acceptable(names, error_msg)
        try:
            node_dict = node_obj.as_dict()
            node = Node(**api_utils.apply_jsonpatch(node_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        self._update_changed_fields(node, node_obj)
        # delta = node_obj.obj_what_changed()
        node_obj.save()
        api_node = Node.convert_with_links(node_obj)
        return api_node
