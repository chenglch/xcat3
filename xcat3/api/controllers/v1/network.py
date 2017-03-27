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
from xcat3.api.controllers.v1 import collection
from xcat3.api.controllers.v1 import utils as api_utils
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3 import objects

CONF = xcat3.conf.CONF

LOG = log.getLogger(__name__)

_DEFAULT_RETURN_FIELDS = ('name', 'reservation', 'created_at', 'nics_info',
                          'state', 'task_action', 'type', 'arch', 'mgt',
                          'updated_at')

_REST_RESOURCE = ('power')



class Network(base.APIBase):
    """API representation of network.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a network.
    """
    name = wsme.wsattr(wtypes.text)
    """The name of network"""
    subnet = wsme.wsattr(types.iptype)
    netmask = wsme.wsattr(types.iptype)
    gateway = wsme.wsattr(types.iptype)
    dhcpserver = wsme.wsattr(types.iptype)
    nameservers = wsme.wsattr(types.iptype)
    ntpservers = {wtypes.text: types.jsontype}
    dynamicrange = {wtypes.text: types.jsontype}
    extra = {wtypes.text: types.jsontype}

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Network.fields)
        for k in fields:
            # Add fields we expose.
            if hasattr(self, k):
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @classmethod
    def get_api_network(cls, name):
        return cls(name=name)

    @staticmethod
    def convert_with_links(net, fields=None):
        network = Network(**net.as_dict())
        return network


class NetworkPatchType(types.JsonPatchType):
    _api_base = Network

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults


class NetworkCollection(collection.Collection):
    """API representation of a collection of nodes."""

    networks = [Network]
    """A list containing network objects"""

    def __init__(self, *args, **kwargs):
        self._type = 'networks'

    @staticmethod
    def convert_with_links(networks, limit=50, url=None, fields=None,
                           **kwargs):
        collection = NetworkCollection()
        collection.networks = [Network.convert_with_links(n, fields=fields)
                               for n in networks]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class NetworkController(rest.RestController):
    invalid_sort_key_list = ['name']

    def _get_networks_collection(self, limit=1000, sort_key='id',
                                 sort_dir='asc', fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})
        filters = {}
        networks = objects.Network.list(pecan.request.context, limit,
                                        sort_key=sort_key, sort_dir=sort_dir,
                                        filters=filters, fields=None)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        return NetworkCollection.convert_with_links(networks, limit,
                                                    fields=fields,
                                                    **parameters)

    def _update_changed_fields(self, network, network_obj):
        """Update rpc_network based on changed fields in a network.

        """
        for field in objects.Network.fields:
            try:
                patch_val = getattr(network, field)
            except AttributeError:
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if network_obj[field] != patch_val:
                network_obj[field] = patch_val

    @expose.expose(Network, types.name, types.listtype)
    def get_one(self, name, fields=None):
        context = pecan.request.context
        network_obj = objects.Network.get_by_name(context, name)
        return Network.convert_with_links(network_obj, fields=fields)

    @expose.expose(NetworkCollection, int, wtypes.text, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of networks.

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
        return self._get_networks_collection(limit, sort_key, sort_dir,
                                             fields=fields)

    @expose.expose(types.jsontype, body=Network,
                   status_code=http_client.CREATED)
    def post(self, network):
        """Create network

        :param network: network with the request
        """
        context = pecan.request.context
        if not hasattr(network, 'name'):
            raise exception.InvalidParameterValue(
                _("Invalid request parameter %(network)s") % {
                    'network': str(network)})
        new_network = objects.Network(context, **network.as_dict())
        new_network.create()
        result = {'network':dict()}
        result['network'][network.name] = 'ok'
        return types.JsonType.validate(result)

    @expose.expose(None, types.name, status_code=http_client.ACCEPTED)
    def delete(self, name):
        """Delete network

        :param nodes: network name to delete, api format
        """
        context = pecan.request.context
        network_obj = objects.Network.get_by_name(context, name)
        network_obj.destroy(name)

    @expose.expose(Network, types.name, body=[NetworkPatchType])
    def patch(self, name, patch):
        """Update an existing network.

        :param name: The name of network.
        :param patch: a json PATCH document to apply to this network.
        :return: json format api node
        """
        context = pecan.request.context
        network_obj = objects.Network.get_by_name(context, name)
        names = api_utils.get_patch_values(patch, '/name')
        if len(names):
            error_msg = (_("Network %s: Cannot change name to invalid name ")
                         % name)
            error_msg += "'%(name)s'"
        try:
            network_dict = network_obj.as_dict()
            network = Network(**api_utils.apply_jsonpatch(network_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        self._update_changed_fields(network, network_obj)
        network_obj.save()
        api_network = Network.convert_with_links(network_obj)
        return api_network
