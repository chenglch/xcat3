# coding=utf-8

import abc
import os
import six
from oslo_config import cfg

from xcat3.common import exception
from xcat3.common import utils
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
        if not mac:
            raise exception.MissingParameterValue(
                _("Node %s does not have any nic with mac address associated "
                  "with it.") % node.name)

        ip = plugin_utils.get_primary_ip_address(node)
        if not ip:
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
    def continue_deploy(self, node):
        """Continue deploy as callback request received

        :param node: the node to act on.
        """

    @abc.abstractmethod
    def clean(self, node):
        """Clean up the generated files during provision

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    def _get_mac_path(self, node, delimiter='-'):
        """Convert a MAC address into a PXE config file name.

            :param mac: A MAC address string in the format xx:xx:xx:xx:xx:xx.
            :param delimiter: The MAC address delimiter. Defaults to dash ('-').
            :param client_id: client_id indicate InfiniBand port.
                              Defaults is None (Ethernet)
            :returns: the path to the config file.
        """
        mac = plugin_utils.get_primary_mac_address(node)
        mac_file_name = mac.replace(':', delimiter).lower()
        mac_file_name = '01-' + mac_file_name
        return os.path.join(self.CONFIG_DIR, mac_file_name)
        return mac_path

    def _get_config_path(self, node):
        return os.path.join(self.CONFIG_DIR, node.name, 'config')

    def _get_osimage_path(self, osimage):
        return os.path.join(CONF.deploy.tftp_dir, 'images',
                            '%s%s' % (osimage.distro, osimage.ver),
                            osimage.arch)

    def _link_mac_configs(self, node):
        """Link each MAC address with the PXE configuration file.

        :param node: the node to act on
        """
        config_path = self._get_config_path(node)
        mac_path = self._get_mac_path(node)
        relative_source_path = os.path.relpath(config_path,
                                               os.path.dirname(mac_path))
        utils.create_link_without_raise(relative_source_path, mac_path)
