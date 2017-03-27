# Copyright 2013 UnitedStack Inc.
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

from oslo_utils import uuidutils
import pecan
from pecan import rest
from six.moves import http_client
import wsme
from wsme import types as wtypes

from xcat3.api.controllers import base
from xcat3.api.controllers import link
from xcat3.api.controllers.v1 import collection
from xcat3.api.controllers.v1 import types

from xcat3 import objects

#Note(chenglch): Not completed

_DEFAULT_RETURN_FIELDS = ('uuid', 'mac')


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
    ip = wsme.wsattr(wtypes.text)
    netmask = wsme.wsattr(wtypes.text)
    extra = {wtypes.text: types.jsontype}
    """This port's meta data"""

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Nics.fields)

        for field in fields:
            # Add fields we expose.
            if hasattr(self, field):
                self.fields.append(field)
                setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(nic, url, fields=None):
        nic_uuid = nic.uuid
        if fields is not None:
            nic.unset_fields_except(fields)

        # never expose the node_id attribute
        nic.node_id = wtypes.Unset
        nic.links = [link.Link.make_link('self', url,
                                          'ports', nic_uuid),
                      link.Link.make_link('bookmark', url,
                                          'ports', nic_uuid,
                                          bookmark=True)
                      ]
        return nic

    @classmethod
    def convert_with_links(cls, rpc_port, fields=None):
        nic = Nic(**rpc_port.as_dict())
        return cls._convert_with_links(nic, pecan.request.public_url,
                                       fields=fields)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     mac='fe:54:00:77:07:d9',
                     extra={'foo': 'bar'},
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow(),
                     primary=True)
        fields = None if expand else _DEFAULT_RETURN_FIELDS
        return cls._convert_with_links(sample, 'http://localhost:6385',
                                       fields=fields)


class NicsPatchType(types.JsonPatchType):
    _api_base = Nic

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults + ['/internal_info']


class NicsCollection(collection.Collection):
    """API representation of a collection of ports."""

    nics = [Nic]
    """A list containing nics objects"""

    def __init__(self, **kwargs):
        self._type = 'nics'

    @staticmethod
    def convert_with_links(rpc_ports, limit, url=None, fields=None, **kwargs):
        collection = NicsCollection()
        collection.ports = [Nic.convert_with_links(p, fields=fields)
                            for p in rpc_ports]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.nics = [Nic.sample(expand=False)]
        return sample
