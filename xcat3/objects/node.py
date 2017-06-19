# coding=utf-8
#    Updated 2017 for xcat test purpose
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
from xcat3.objects import nic as nic_object


@base.XCAT3ObjectRegistry.register
class Node(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1'

    dbapi = db_api.get_instance()

    fields = {
        # id may be None while construct the ndoe object
        'id': object_fields.IntegerField(nullable=True),
        'name': object_fields.StringField(),
        'arch': object_fields.StringField(nullable=True),
        'netboot': object_fields.StringField(nullable=False),
        'type': object_fields.StringField(nullable=True),
        'reservation': object_fields.StringField(nullable=True),
        'mgt': object_fields.StringField(nullable=True),
        'state': object_fields.StringField(nullable=True),
        'nics_info': object_fields.FlexibleDictField(nullable=True),
        'osimage_info': object_fields.FlexibleDictField(nullable=True),
        'scripts_info': object_fields.FlexibleDictField(nullable=True),
        'control_info': object_fields.FlexibleDictField(nullable=True),
        'console_info': object_fields.FlexibleDictField(nullable=True),
        'conductor_affinity': object_fields.IntegerField(nullable=True),
        'osimage_id': object_fields.IntegerField(nullable=True),
        # NOTE: passwd_id is not used currently
        'passwd_id': object_fields.IntegerField(nullable=True),
    }

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

    @classmethod
    def get_by_id(cls, context, node_id):
        """Find a node based on its integer id and return a Node object.

        :param node_id: the id of a node.
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_id(node_id)
        node = cls._from_db_object(cls(context), db_node)
        return node

    @classmethod
    def get_by_name(cls, context, name):
        """Find a node based on name and return a Node object.

        :param name: the logical name of a node.
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_name(name)
        node = cls._from_db_object(cls(context), db_node)
        nics_info = nic_object.Nic.get_nics_info_from_node(node.id)
        setattr(node, 'nics_info', nics_info)
        return node

    @classmethod
    def list(cls, context, sort_key=None, sort_dir=None, filters=None,
             fields=None):
        """Return a list of Node objects.

        :param context: Security context.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Node` object.

        """
        db_nodes = cls.dbapi.get_node_list(filters=filters,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir,
                                           fields=fields)
        nodes = cls._from_db_object_list(context, db_nodes)

        if not fields or 'nics_info' not in fields:
            return nodes

        for node in nodes:
            nics_info = nic_object.Nic.get_nics_info_from_node(node.id)
            setattr(node, 'nics_info', nics_info)
        return nodes

    @classmethod
    def list_in(cls, context, names, filters=None, obj_info=None):
        """Return a list of Node objects within the names

        :returns: a list of :class:`Node` object with nics info
        """
        db_nodes = cls.dbapi.get_node_in(names, filters)
        nodes = cls._from_db_object_list(context, db_nodes)

        if obj_info and 'nics' in obj_info:
            nic_object.Nic.to_node_objs_with_nics_info(nodes)
        return nodes

    @classmethod
    def reserve_nodes(cls, context, tag, node_names, obj_info=None):
        db_nodes = cls.dbapi.reserve_nodes(tag, node_names)
        nodes = cls._from_db_object_list(context, db_nodes)

        if obj_info and 'nics' in obj_info:
            nic_object.Nic.to_node_objs_with_nics_info(nodes)
        return nodes

    @classmethod
    def release_nodes(cls, context, tag, node_names):
        cls.dbapi.release_nodes(tag, node_names)

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

    @classmethod
    def create_nodes(cls, nodes_values):
        values = []
        for node in nodes_values:
            value = node.obj_get_changes()
            values.append(value)
        db_nodes = cls.dbapi.create_nodes(values)

    def validate(self, context):
        """validate node properties before creating or updating nodes"""
        value = self.obj_get_changes()
        for field in self.fields:
            self[field] = value.get(field)

        if self['nics_info'] and self['nics_info'].has_key('nics'):
            nics = self['nics_info']['nics']
            for nic in nics:
                nic_obj = nic_object.Nic(context, **nic)
                nic_obj.validate(context)


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
        """Delete nodes from the DB.

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

    @classmethod
    def update_nodes(cls, nodes):
        """Update nodes attributes, used for patch interface

        :param nodes: the node objects

        """
        updates_dict = {}
        for node in nodes:
            updates = node.obj_get_changes()
            updates_dict[node.id] = updates
        cls.dbapi.update_nodes(updates_dict)

    @classmethod
    def save_nodes(cls, nodes, context=None):
        """Save updates to nodes with task manager


        :param nodes: the nodes contains changes
        :param context: Security context.
        :raises: InvalidParameterValue if some property values are invalid.
        """
        node_ids = []
        updates_dict = {}
        for node in nodes:
            updates = node.obj_get_changes()
            updates_dict[node.id] = updates
            node_ids.append(node.id)
        cls.dbapi.save_nodes(node_ids, updates_dict)
