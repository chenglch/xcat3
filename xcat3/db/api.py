# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Updated 2017 for xcat test purpose
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six

_BACKEND_MAPPING = {'sqlalchemy': 'xcat3.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_nodeinfo_list(self, columns=None, filters=None, sort_key=None,
                          sort_dir=None):
        """Get specific columns for matching nodes.

        Return a list of the specified columns for all nodes that match the
        specified filters.

        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.
                        :reserved: True | False
                        :reserved_by_any_of: [conductor1, conductor2]
                        :provision_state: provision state of node
                        :provisioned_before:
                            nodes with provision_updated_at field before this
                            interval in seconds
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def get_node_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None, fields=None):
        """Return a list of nodes.

        :param filters: Filters to apply. Defaults to None.

                        :associated: True | False
                        :reserved: True | False
                        :provision_state: provision state of node
                        :provisioned_before:
                            nodes with provision_updated_at field before this
                            interval in seconds
        :param limit: Maximum number of nodes to return.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        """

    @abc.abstractmethod
    def get_node_in(self, names, filters=None):
        """ Get nodes collection within names

        :param names: the nodes names to select
        :param filters: Filters to apply. Defaults to None.
        :return: a list of nodes
        """

    @abc.abstractmethod
    def reserve_nodes(self, tag, node_names):
        """Reserve nodes.

        :param tag: A string uniquely identifying the reservation holder.
        :param node_names: The name of nodes.
        :return object of nodes
        :raises: NodeNotFound if the node is not found.
        :raises: NodeLocked if the node is already reserved.
        """

    @abc.abstractmethod
    def release_nodes(self, tag, node_names):
        """Release the reservation on nodes

        :param tag: A string uniquely identifying the reservation holder.
        :param node_names: The name of nodes.
        :raises: NodeNotFound if the node is not found.
        :raises: NodeLocked if the node is reserved by another host.
        :raises: NodeNotLocked if the node was found to not have a
                 reservation at all.
        """

    @abc.abstractmethod
    def create_node(self, values):
        """Create a new node.

        :param values: A dict containing several items used to identify
                       and track the node. For example:

                       ::

                        {
                         'name": 'test_node'
                         'mgt': 'ipmi',
                         'control_info': {'ipmi_address':'10.0.0.1',
                                          'ipmi_user': 'admin'}
                        }
        :returns: A node.
        """

    @abc.abstractmethod
    def create_nodes(self, nodes_values):
        """Create nodes"""

    @abc.abstractmethod
    def get_node_by_id(self, node_id):
        """Return a node.

        :param node_id: The id of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def destroy_node(self, node_name):
        """Destroy a node and its associated resources.

        :param node_id: The name of a node.
        """

    @abc.abstractmethod
    def destroy_nodes(self, node_ids):
        """Destroy nodes and its associated resources.

        :param node_ids: The ids of nodes.
        """

    @abc.abstractmethod
    def get_node_by_name(self, node_name):
        """Return a node.

        :param node_name: The name of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def update_nodes(self, updates_dict):
        """Update node attributes

        :updates_dict: patch for nodes
        """

    @abc.abstractmethod
    def save_nodes(self, node_ids, updates_dict):
        """Update node attributes for task object

        :node_ids: ids of nodes
        :updates_dict: patch for node
        :returns: db nodes
        """

    @abc.abstractmethod
    def get_nic_by_id(self, id):
        """Get nic from id"""

    @abc.abstractmethod
    def get_nic_by_uuid(self, uuid):
        """Get nic from uuid"""

    @abc.abstractmethod
    def get_nic_by_mac(self, mac):
        """Get nic from mac"""

    @abc.abstractmethod
    def get_nic_list(self):
        """List all the nics"""

    @abc.abstractmethod
    def get_nics_by_node_id(self, node_id, limit=None, sort_key=None,
                            sort_dir=None):
        """List nics owned by the specific node"""

    @abc.abstractmethod
    def create_nic(self, values):
        """Create nic"""

    @abc.abstractmethod
    def update_nic(self, nic_id, values):
        """update nic"""

    @abc.abstractmethod
    def destroy_nic(self, nic_id):
        """destroy nic"""

    @abc.abstractmethod
    def get_network_by_id(self, id):
        """Get network from network id"""

    @abc.abstractmethod
    def get_network_by_name(self, name):
        """Get network from network name"""

    @abc.abstractmethod
    def get_network_list(self, filters=None):
        """Get network list from networks table"""

    @abc.abstractmethod
    def create_network(self, values):
        """Create network in networks table"""

    @abc.abstractmethod
    def destroy_network(self, name):
        """Destroy network"""

    @abc.abstractmethod
    def update_network(self, network_id, values):
        """Update network"""

    @abc.abstractmethod
    def get_dhcp_list(self):
        """List dhcp options"""

    @abc.abstractmethod
    def save_or_update_dhcp(self, names, dhcp_opts):
        """Update dhcp options"""

    @abc.abstractmethod
    def destroy_dhcp(self, names):
        """Destroy dhcp options"""

    @abc.abstractmethod
    def get_services(self, type='conductor'):
        """Return conductor nodes

        :returns: Conductor nodes
        """

    @abc.abstractmethod
    def get_service_from_id(self, id):
        """Return conductor node from service id

        :param id: service id
        :returns: Conductor node

        """

    @abc.abstractmethod
    def register_service(self, values, update_existing=False):
        """Register conductor nodes"""

    @abc.abstractmethod
    def get_image_by_id(self, id):
        """Get image from id"""

    @abc.abstractmethod
    def get_image_by_name(self, name):
        """Get image from name"""

    @abc.abstractmethod
    def get_image_list(self):
        """Get image list"""

    @abc.abstractmethod
    def create_image(self, values):
        """Create image"""

    @abc.abstractmethod
    def destroy_image(self, name):
        """Delete image"""

    @abc.abstractmethod
    def update_image(self, osimage_id, values):
        """Update image"""

    @abc.abstractmethod
    def get_passwd_by_id(self, id):
        """Get Passwd"""

    @abc.abstractmethod
    def get_passwd_by_key(self, key):
        """Get Passwd"""

    @abc.abstractmethod
    def get_passwd_list(self):
        """Get passwd object list"""

    @abc.abstractmethod
    def create_passwd(self, values):
        """Create Passwd object"""

    @abc.abstractmethod
    def destroy_passwd(self, key):
        """Delete Passwd object"""

    @abc.abstractmethod
    def update_passwd(self, pwsswd_id, values):
        """Update attribute for Passwd object"""
