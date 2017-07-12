# coding=utf-8

import jinja2
import os
import weakref
from oslo_utils import fileutils
from oslo_config import cfg

from xcat3.common import boot_device as support_bdev
from xcat3.common import exception
from xcat3.common import utils
from xcat3.plugins import utils as plugin_utils
from xcat3.plugins.boot import base

CONF = cfg.CONF


class Petitboot(base.BootInterface):
    CONFIG_DIR = os.path.join(CONF.deploy.install_dir, 'boot')
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    TRY_DISK_BOOT_STR = '#boot'

    def __init__(self):
        fileutils.ensure_tree(self.CONFIG_DIR)
        self.tmpl = None

    def _get_config_path(self, node):
        return os.path.join(self.CONFIG_DIR, node.name)

    def _get_config_url(self, node):
        return "http://%(ip)s/install/boot/%(node)s" % {
            'ip': CONF.conductor.host_ip, 'node': node.name}

    def _create_config(self, node, opts):
        if self.tmpl is None or self.tmpl() is None:
            template = os.path.join(self.BASEDIR, 'petitboot.template')
            tmpl_path, tmpl_name = os.path.split(template)
            loader = jinja2.FileSystemLoader(tmpl_path)
            env = jinja2.Environment(loader=loader)
            self.tmpl = weakref.ref(env.get_template(tmpl_name))

        tmpl = self.tmpl()
        cfg = tmpl.render(opts)
        cfg_file = self._get_config_path(node)
        utils.write_to_file(cfg_file, cfg)

    def clean(self, node):
        utils.unlink_without_raise(self._get_config_path(node))

    def gen_dhcp_opts(self, node):
        """Generate dhcp option dict for petitboot configuration

        :param node: the node to act on.
        :returns dhcp_opts: dhcp option dict for this node
        :raises: MissingParameterValue if a required parameter is missing.
        """
        dhcp_opts = {
            'mac': node.mac,
            'ip': node.ip,
            'hostname': node.name,
            '209': self._get_config_url(node),
            '66': CONF.conductor.host_ip,
            '12': node.name, '15': node.name}
        return dhcp_opts

    def build_boot_conf(self, node, os_boot_str, osimage):
        """Build the configuration file and prepare kernal and initrd

        :param node: the node to act on.
        :param os_boot_str: the boot parameters from os plugin.
        :param osimage: the os image object create by copycds.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        osimage_path = plugin_utils.get_http_root_for_osimage(osimage)
        kernel = os.path.join(osimage_path, 'xcat', 'vmlinuz')
        if not os.path.exists(kernel):
            raise exception.FileNotFound(file=kernel)

        initrd = os.path.join(osimage_path, 'xcat', 'initrd.img')
        if not os.path.exists(initrd):
            raise exception.FileNotFound(file=initrd)

        url = plugin_utils.get_http_url_for_osimage(osimage)
        kernel_url = "%s/xcat/vmlinuz" % url
        initrd_url = "%s/xcat/initrd.img" % url
        opts = {'kernel': kernel_url, 'initrd': initrd_url,
                'host_ip': CONF.conductor.host_ip,
                'node': node.name,
                'os_boot_str': os_boot_str}
        self._create_config(node, opts)

    def continue_deploy(self, node, plugin_map):
        """Continue deploy as callback request received

        :param node: the node to act on.
        :param plugin_map: the dict of plugins.
        """
        config_path = self._get_config_path(node)
        utils.write_to_file(config_path, self.TRY_DISK_BOOT_STR)
        control_plugin = plugin_map.get_control_plugin(node)
        control_plugin.set_boot_device(node, support_bdev.DISK)
