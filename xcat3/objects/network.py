# coding=utf-8
#
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

from oslo_utils import strutils
from oslo_versionedobjects import base as object_base

from xcat3.common import exception
from xcat3.db import api as db_api
from xcat3.objects import base
from xcat3.objects import fields as object_fields



@base.XCAT3ObjectRegistry.register
class Network(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1'

    dbapi = db_api.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'name': object_fields.StringField(nullable=False),
        'subnet': object_fields.StringField(nullable=True),
        'netmask': object_fields.StringField(nullable=True),
        'gateway': object_fields.StringField(nullable=True),
        'dhcpserver': object_fields.StringField(nullable=True),
        'nameservers': object_fields.StringField(nullable=True),
        'ntpservers': object_fields.FlexibleDictField(nullable=True),
        'dynamic_range': object_fields.FlexibleDictField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
    }

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_id(cls, context, network_id):
        """Find a network based on its integer id and return a Network object.

        :param network_id: the id of a node.
        :returns: a :class:`Network` object.
        """
        db_network = cls.dbapi.get_network_by_id(network_id)
        network = cls._from_db_object(cls(context), db_network)
        return network

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_name(cls, context, name):
        """Find a network based on name and return a Network object.

        :param name: the name of a network.
        :returns: a :class:`Network` object.
        """
        db_network = cls.dbapi.get_network_by_name(name)
        network = cls._from_db_object(cls(context), db_network)
        return network

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def list(cls, context, limit=None, sort_key=None, sort_dir=None,
             filters=None, fields=None):
        """Return a list of Node objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Network` object.

        """
        db_networks = cls.dbapi.get_network_list(filters=filters, limit=limit,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)
        networks = cls._from_db_object_list(context, db_networks)
        return networks

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def create(self, context=None):
        """Create a network record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        values = self.obj_get_changes()
        db_network = self.dbapi.create_network(values)
        self._from_db_object(self, db_network)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def destroy(self, context=None):
        """Delete the network from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        self.dbapi.destroy_network(self.name)
        self.obj_reset_changes()

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def save(self, context=None):
        """Save updates to this Node.

        Column-wise updates will be made based on the result of
        self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        updates = self.obj_get_changes()
        db_network = self.dbapi.update_network(self.id, updates)

        # TODO(galyna): updating specific field not touching others to not
        # change default behaviour. Otherwise it will break a bunch of tests
        # This can be updated in other way when more fields like `updated_at`
        # will appear
        self.updated_at = db_network['updated_at']
        self.obj_reset_changes()
