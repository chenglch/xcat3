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

from oslo_utils import netutils
from oslo_utils import strutils
from oslo_utils import uuidutils
from oslo_versionedobjects import base as object_base

from xcat3.common import exception
from xcat3.db import api as dbapi
from xcat3.objects import base
from xcat3.objects import fields as object_fields


# Note(chenglch): this part is not completed

@base.XCAT3ObjectRegistry.register
class Nics(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'uuid': object_fields.UUIDField(nullable=True),
        'name': object_fields.StringField(nullable=True),
        'node_id': object_fields.IntegerField(nullable=True),
        'mac': object_fields.MACAddressField(nullable=True),
        'ip': object_fields.StringField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
    }

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get(cls, context, id):
        """Find a nic.

        Find a nic based on its id or uuid or MAC address and return a Nic
        object.

        :param id: the id *or* uuid *or* MAC address of a nic.
        :returns: a :class:`Nic` object.
        :raises: InvalidIdentity

        """
        if strutils.is_int_like(id):
            return cls.get_by_id(context, id)
        elif uuidutils.is_uuid_like(id):
            return cls.get_by_uuid(context, id)
        elif netutils.is_valid_mac(id):
            return cls.get_by_address(context, id)
        else:
            raise exception.InvalidIdentity(identity=id)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_id(cls, context, id):
        """Find a nic based on its integer id and return a Nic object.

        :param id: the id of a nic.
        :returns: a :class:`Nic` object.
        :raises: NicNotFound

        """
        db_nic = cls.dbapi.get_nic_by_id(id)
        nic = cls._from_db_object(cls(context), db_nic)
        return nic

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a nic based on uuid and return a :class:`Nic` object.

        :param uuid: the uuid of a nic.
        :param context: Security context
        :returns: a :class:`Nic` object.
        :raises: NicNotFound

        """
        db_nic = cls.dbapi.get_nic_by_uuid(uuid)
        nic = cls._from_db_object(cls(context), db_nic)
        return nic

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_mac(cls, context, mac):
        """Find a nic based on address and return a :class:`Nic` object.

        :param address: the address of a nic.
        :param context: Security context
        :returns: a :class:`Nic` object.
        :raises: NicNotFound

        """
        db_nic = cls.dbapi.get_nic_by_mac(mac)
        nic = cls._from_db_object(cls(context), db_nic)
        return nic

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def list(cls, context, limit=None, sort_key=None, sort_dir=None):
        """Return a list of Nic objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Nic` object.
        :raises: InvalidParameterValue

        """
        db_nics = cls.dbapi.get_nic_list(limit=limit,
                                         sort_key=sort_key,
                                         sort_dir=sort_dir)
        return cls._from_db_object_list(context, db_nics)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def list_by_node_id(cls, context, node_id, limit=None, sort_key=None,
                        sort_dir=None):
        """Return a list of Nic objects associated with a given node ID.

        :param context: Security context.
        :param node_id: the ID of the node.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Nic` object.

        """
        db_nics = cls.dbapi.get_nics_by_node_id(node_id, limit=limit,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)
        return cls._from_db_object_list(context, db_nics)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def create(self, context=None):
        """Create a Nic record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Nic(context)
        :raises: MACAlreadyExists if 'address' column is not unique
        :raises: NicAlreadyExists if 'uuid' column is not unique

        """
        values = self.obj_get_changes()
        db_nic = self.dbapi.create_nic(values)
        self._from_db_object(self, db_nic)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def destroy(self, context=None):
        """Delete the Nic from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Nic(context)
        :raises: NicNotFound

        """
        self.dbapi.destroy_nic(self.uuid)
        self.obj_reset_changes()

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def save(self, context=None):
        """Save updates to this Nic.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Nic(context)
        :raises: NicNotFound
        :raises: MACAlreadyExists if 'address' column is not unique

        """
        pass
        # updates = self.obj_get_changes()
        # updated_nic = self.dbapi.update_nic(self.uuid, updates)
        # self._from_db_object(self, updated_nic)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def refresh(self, context=None):
        """Loads updates for this Nic.

        Loads a nic with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded nic column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Nic(context)
        :raises: NicNotFound

        """
        current = self.get_by_uuid(self._context, uuid=self.uuid)
        self.obj_refresh(current)
