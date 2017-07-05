# coding=utf-8

import abc
import os
import six
from oslo_config import cfg

from xcat3.common import exception
from xcat3.plugins import base
from xcat3.plugins import utils as plugin_utils


CONF = cfg.CONF


@six.add_metaclass(abc.ABCMeta)
class BootInterface(base.BaseInterface):
    """Interface for hardware control actions."""
    CONFIG_DIR = None
    BASEDIR = None

    def validate(self, node):
        """validate the specific attribute

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        mac = plugin_utils.get_primary_mac_address(node)
        if mac is None:
            raise exception.MissingParameterValue(
                _("Node %s does not have any nic with mac address associated "
                  "with it.") % node.name)

        ip = plugin_utils.get_primary_ip_address(node)
        if ip is None:
            raise exception.MissingParameterValue(
                _("Node %s does not have any nic with ip address associated "
                  "with it.") % node.name)

        setattr(node, 'mac', mac)
        setattr(node, 'ip', ip)

    @abc.abstractmethod
    def gen_dhcp_opts(self, node):
        """Build the configuration file and prepare kernal and initrd

        :param node: the node to act on.
        :returns dhcp_opts: dhcp option dict for this node
        :raises: MissingParameterValue if a required parameter is missing.
        """

    @abc.abstractmethod
    def build_boot_conf(self, node, os_boot_str, osimage):
        """Build the configuration file and prepare kernal and initrd

        :param node: the node to act on.
        :param os_boot_str: the boot parameters from os plugin.
        :param osimage: the os info create by copycds.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    @abc.abstractmethod
    def continue_deploy(self, node, plugin_map):
        """Continue deploy as callback request received

        :param node: the node to act on.
        :param plugin_map: the dict of plugins.
        """

    @abc.abstractmethod
    def clean(self, node):
        """Clean up the generated files during provision

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
