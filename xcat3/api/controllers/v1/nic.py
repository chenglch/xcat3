# Copyright 2013 UnitedStack Inc.
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

import pecan
from pecan import rest
from six.moves import http_client
import wsme
from wsme import types as wtypes

from xcat3.api import expose
from xcat3.api.controllers import base
from xcat3.api.controllers.v1 import collection
from xcat3.api.controllers.v1 import utils as api_utils
from xcat3.api.controllers.v1 import types
from xcat3.common import exception
from xcat3.common import states

from xcat3 import objects

_DEFAULT_RETURN_FIELDS = ('uuid', 'mac')
dbapi = base.dbapi


class Nic(base.APIBase):
    """API representation of a port.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a port.
    """

    uuid = types.uuid
    """Unique UUID for this nic"""
    mac = wsme.wsattr(types.macaddress, mandatory=True)
    """MAC Address for this nic"""
    name = wsme.wsattr(wtypes.text)
    """name for this nic"""
    ip = wsme.wsattr(types.iptype)
    netmask = wsme.wsattr(types.iptype)
    extra = {wtypes.text: types.jsontype}
    """This nics's meta data"""
    # NOTE(chenglch): For post purpose, to accept node name
    node = wsme.wsattr(wtypes.text)
    primary = types.boolean
    node_id = wsme.wsattr(int)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Nic.fields)

        for field in fields:
            # Add fields we expose.
            if hasattr(self, field):
                self.fields.append(field)
                setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(nic, url, fields=None):
        if fields is not None:
            nic.filter_fields(fields)

        # never expose the node_id attribute
        nic.node_id = wtypes.Unset
        nic.ip = unicode(nic.ip) if nic.ip is not None else None
        return nic

    @classmethod
    def convert_with_links(cls, nic_obj, fields=None):
        nic = Nic(**nic_obj.as_dict())
        node = objects.Node.get_by_id(pecan.request.context, nic_obj.node_id)
        if not fields or 'node' in fields:
            nic.fields.append('node')
            setattr(nic, 'node', node.name)
        return cls._convert_with_links(nic, pecan.request.public_url,
                                       fields=fields)


class NicPatchType(types.JsonPatchType):
    _api_base = Nic

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults + ['/internal_info']


class NicCollection(collection.Collection):
    """API representation of a collection of nics."""

    nics = [Nic]
    """A list containing nics objects"""

    def __init__(self, **kwargs):
        self._type = 'nics'

    @staticmethod
    def convert_with_links(nics, limit, url=None, fields=None, **kwargs):
        collection = NicCollection()
        collection.nics = [Nic.convert_with_links(n, fields=fields)
                           for n in nics]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class NicController(rest.RestController):
    invalid_sort_key_list = ['name']

    _custom_actions = {
        'node': ['GET'],
        'address': ['GET'],
    }

    def _update_changed_fields(self, nic, nic_obj):
        """Update rpc_nic based on changed fields in a nic.

        """
        for field in objects.Nic.fields:
            try:
                patch_val = getattr(nic, field)
            except AttributeError:
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if nic_obj[field] != patch_val:
                nic_obj[field] = patch_val

    @expose.expose(NicCollection, types.name, types.listtype)
    def node(self, node_name, fields=None):
        context = pecan.request.context
        node_obj = objects.Node.get_by_name(context, node_name)
        nics = objects.Nic.list_by_node_id(context, node_obj.id)
        parameters = {'sort_key': 'id', 'sort_dir': 'asc'}
        return NicCollection.convert_with_links(nics, 1000,
                                                fields=fields,
                                                **parameters)

    @expose.expose(Nic, wtypes.text, types.listtype)
    def address(self, mac, fields=None):
        context = pecan.request.context
        nic_obj = objects.Nic.get_by_mac(context, mac)
        return Nic.convert_with_links(nic_obj, fields=fields)

    @expose.expose(Nic, types.uuid, types.listtype)
    def get_one(self, uuid, fields=None):
        context = pecan.request.context
        nic_obj = objects.Nic.get_by_uuid(context, uuid)
        return Nic.convert_with_links(nic_obj, fields=fields)

    @expose.expose(types.jsontype)
    def get_all(self):
        """Retrieve a list of nics. """
        db_nics = dbapi.get_nic_list()
        result = dict()
        result['nics'] = [{'uuid': nic[0], 'mac': nic[1]} for nic in db_nics]
        return result

    @expose.expose(types.jsontype, body=Nic,
                   status_code=http_client.CREATED)
    def post(self, nic):
        """Create nic

        :param nic: nic with the request
        """
        context = pecan.request.context
        if nic.node_id == wtypes.Unset:
            if nic.node != wtypes.Unset:
                node_obj = objects.Node.get_by_name(context, nic.node)
                setattr(nic, 'node_id', node_obj.id)
                delattr(nic, 'node')
            else:
                raise exception.InvalidNicAttr(mac=nic.mac)

        new_nic = objects.Nic(context, **nic.as_dict())
        new_nic.create()
        result = dict()
        result[new_nic.mac] = states.SUCCESS
        return types.JsonType.validate(result)

    @expose.expose(None, types.uuid,
                   status_code=http_client.ACCEPTED)
    def delete(self, uuid):
        """Delete nic

        :param nodes: nic uuid to delete, api format
        """
        context = pecan.request.context
        nic_obj = objects.Nic.get_by_uuid(context, uuid)
        nic_obj.destroy()

    @expose.expose(Nic, types.uuid, body=[NicPatchType])
    def patch(self, uuid, patch):
        """Update an existing nic.

        :param name: The uuid of nic.
        :param patch: a json PATCH document to apply to this nic.
        :return: json format api node
        """

        def _update_node_attr(context, nic_obj, patch):
            i = 0
            while i < len(patch):
                p = patch[i]
                if p['path'].lstrip('/') == 'node':
                    node = objects.Node.get_by_name(context, p['value'])
                    p['value'] = node.id
                    p['path'] = '/node_id'
                i += 1

        context = pecan.request.context
        nic_obj = objects.Nic.get_by_uuid(context, uuid)
        try:
            _update_node_attr(context, nic_obj, patch)
            nic_dict = nic_obj.as_dict()
            nic = Nic(**api_utils.apply_jsonpatch(nic_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        self._update_changed_fields(nic, nic_obj)
        nic_obj.save()
        api_nic = Nic.convert_with_links(nic_obj)
        return api_nic
