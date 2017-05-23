# coding=utf-8

import os
from oslo_utils import fileutils
from oslo_config import cfg

from xcat3.common import exception
from xcat3.common import utils
from xcat3.plugins.boot import base

CONF = cfg.CONF


class PXEBoot(base.BootInterface):
    CONFIG_DIR = os.path.join(CONF.deploy.tftp_dir, 'pxelinux.cfg')
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    TRY_DISK_BOOT_STR = 'DEFAULT xCAT\nLABEL xCAT\nLOCALBOOT 0\n'

    def __init__(self):
        fileutils.ensure_tree(self.CONFIG_DIR)

    def _create_config(self, node, opts):
        template = os.path.join(self.BASEDIR, 'pxe_boot.template')
        cfg = utils.render_template(template, opts)
        cfg_file = self._get_config_path(node)
        fileutils.ensure_tree(os.path.dirname(cfg_file))
        utils.write_to_file(cfg_file, cfg)

    def _get_node_path(self, node):
        return os.path.join(CONF.deploy.tftp_dir, 'nodes', node.name)

    def clean(self, node):
        mac_path = self._get_mac_path(node)
        utils.unlink_without_raise(mac_path)
        utils.rmtree_without_raise(self._get_node_path(node))
        utils.rmtree_without_raise(
            os.path.dirname(self._get_config_path(node)))

    def gen_dhcp_opts(self, node):
        """Build the configuration file and prepare kernal and initrd

        :param node: the node to act on.
        :returns dhcp_opts: dhcp option dict for this node
        :raises: MissingParameterValue if a required parameter is missing.
        """

        dhcp_opts = {
            'mac': node.mac,
            'ip': node.ip,
            'hostname': node.name,
            '67': {'ScaleMP': 'vsmp/pxelinux.0', 'other': 'pxelinux.0'},
            '66': CONF.conductor.host_ip,
            '12': node.name, '15': node.name}
        return dhcp_opts

    def build_boot_conf(self, node, os_boot_str, osimage):
        """Build the configuration file and prepare kernal and initrd

        :param node: the node to act on.
        :param os_boot_str: the boot parameters from os plugin.
        :param osimage: the os info create by copycds.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        node_path = self._get_node_path(node)
        osimage_path = self._get_osimage_path(osimage)
        self.clean(node)
        fileutils.ensure_tree(node_path)
        kernel = os.path.join(osimage_path, 'vmlinuz')
        if not os.path.exists(kernel) or not os.access(kernel, os.R_OK):
            raise exception.FileNotFound(file=kernel)

        initrd = os.path.join(osimage_path, 'initrd.img')
        if not os.path.exists(initrd) or not os.access(initrd, os.R_OK):
            raise exception.FileNotFound(file=initrd)

        link_kernel = os.path.join(node_path, 'vmlinuz')
        link_initrd = os.path.join(node_path, 'initrd.img')

        # create link for tftp transfer
        relative_source_path = os.path.relpath(kernel,
                                               os.path.dirname(link_kernel))
        utils.create_link_without_raise(relative_source_path, link_kernel)
        relative_source_path = os.path.relpath(initrd,
                                               os.path.dirname(link_initrd))
        utils.create_link_without_raise(relative_source_path, link_initrd)

        opts = {'kernel': link_kernel, 'initrd': link_initrd,
                'host_ip': CONF.conductor.host_ip,
                'node': node.name,
                'os_boot_str': os_boot_str}
        self._create_config(node, opts)
        self._link_mac_configs(node)

    def continue_deploy(self, node):
        """Continue deploy as callback request received

        :param node: the node to act on.
        """
        config_path = self._get_config_path(node)
        utils.write_to_file(config_path, self.TRY_DISK_BOOT_STR)
