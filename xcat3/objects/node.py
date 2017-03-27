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
from xcat3.objects import nics as nics_object

_UNSET_NICS_FIELDS = ('updated_at', 'created_at', 'id', 'node_id')


@base.XCAT3ObjectRegistry.register
class Node(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1'

    dbapi = db_api.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'name': object_fields.StringField(nullable=True),
        'arch': object_fields.StringField(nullable=True),
        'type': object_fields.StringField(nullable=True),
        'reservation': object_fields.StringField(nullable=True),
        'mgt': object_fields.StringField(nullable=True),
        'state': object_fields.StringField(nullable=True),
        'nics_info': object_fields.FlexibleDictField(nullable=True),
        'osimage_info': object_fields.FlexibleDictField(nullable=True),
        'scripts_info': object_fields.FlexibleDictField(nullable=True),
        'control_info': object_fields.FlexibleDictField(nullable=True),
        'console_info': object_fields.FlexibleDictField(nullable=True),
    }

    @classmethod
    def _get_nics_info(cls, context, node_id):
        nics = nics_object.Nics.list_by_node_id(context, node_id)
        nics_info = dict()
        nics_info['nics'] = []
        for nic in nics:
            for field in _UNSET_NICS_FIELDS:
                delattr(nic, field)
            nic = nic.as_dict()
            nics_info['nics'].append(nic)
        return nics_info

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get(cls, context, node_id):
        """Find a node based on its id and return a Node object.

        :param node_id: the id of a node.
        :returns: a :class:`Node` object.
        """
        if strutils.is_int_like(node_id):
            return cls.get_by_id(context, node_id)
        else:
            raise exception.InvalidIdentity(identity=node_id)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_id(cls, context, node_id):
        """Find a node based on its integer id and return a Node object.

        :param node_id: the id of a node.
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_id(node_id)
        node = cls._from_db_object(cls(context), db_node)
        return node

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def get_by_name(cls, context, name):
        """Find a node based on name and return a Node object.

        :param name: the logical name of a node.
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_name(name)
        node = cls._from_db_object(cls(context), db_node)
        nics_info = cls._get_nics_info(context, node.id)
        setattr(node, 'nics_info', nics_info)
        return node

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
        :returns: a list of :class:`Node` object.

        """
        db_nodes = cls.dbapi.get_node_list(filters=filters, limit=limit,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)
        nodes = cls._from_db_object_list(context, db_nodes)
        if not fields or 'nics_info' not in fields:
            return nodes

        for node in nodes:
            nics_info = cls._get_nics_info(context, node.id)
            setattr(node, 'nics_info', nics_info)
        return nodes

    @classmethod
    def list_in(cls, context, names, filters=None, objs=['nics']):
        """Return a list of Node objects within the names


        :returns: a list of :class:`Node` object with nics info
        """
        db_nodes = cls.dbapi.get_node_in(names, filters)
        nodes = cls._from_db_object_list(context, db_nodes)
        if objs and 'nics' in objs:
            for node in nodes:
                nics_info = cls._get_nics_info(context, node.id)
                setattr(node, 'nics_info', nics_info)
        return nodes

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def reserve(cls, context, tag, node_id):
        """Get and reserve a node.

        To prevent other ManagerServices from manipulating the given
        Node while a Task is performed, mark it reserved by this host.

        :param context: Security context.
        :param tag: A string uniquely identifying the reservation holder.
        :param node_id: A node id
        :raises: NodeNotFound if the node is not found.
        :returns: a :class:`Node` object.

        """
        db_node = cls.dbapi.reserve_node(tag, node_id)
        node = cls._from_db_object(cls(context), db_node)
        return node

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable_classmethod
    @classmethod
    def release(cls, context, tag, node_id):
        """Release the reservation on a node.

        :param context: Security context.
        :param tag: A string uniquely identifying the reservation holder.
        :param node_id: A node id
        :raises: NodeNotFound if the node is not found.

        """
        cls.dbapi.release_node(tag, node_id)

    @classmethod
    def reserve_nodes(cls, context, tag, node_names):
        db_nodes = cls.dbapi.reserve_nodes(tag, node_names)
        nodes = cls._from_db_object_list(context, db_nodes)
        for node in nodes:
            nics_info = cls._get_nics_info(context, node.id)
            setattr(node, 'nics_info', nics_info)
        return nodes

    @classmethod
    def release_nodes(cls, context, tag, node_names):
        cls.dbapi.release_nodes(tag, node_names)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def create(self, context=None):
        """Create a Node record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        node before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        values = self.obj_get_changes()
        db_node = self.dbapi.create_node(values)
        self._from_db_object(self, db_node)

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def destroy(self, context=None):
        """Delete the Node from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        self.dbapi.destroy_node(self.name)
        self.obj_reset_changes()

    @classmethod
    def destroy_nodes(cls, nodes, context=None):
        """Delete the Node from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        ids = [node.id for node in nodes]
        cls.dbapi.destroy_nodes(ids)
        for node in nodes:
            node.obj_reset_changes()

    # NOTE(xek): We don't want to enable RPC on this call just yet. Remotable
    # methods can be used in the future to replace current explicit RPC calls.
    # Implications of calling new remote procedures should be thought through.
    # @object_base.remotable
    def save(self, context=None):
        """Save updates to this Node.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        node before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        updates = self.obj_get_changes()
        db_node = self.dbapi.update_node(self.id, updates)

        # TODO(galyna): updating specific field not touching others to not
        # change default behaviour. Otherwise it will break a bunch of tests
        # This can be updated in other way when more fields like `updated_at`
        # will appear
        self.updated_at = db_node['updated_at']
        self.obj_reset_changes()
