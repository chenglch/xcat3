# coding=utf-8

import os
from oslo_config import cfg

from xcat3.plugins.osimage import base
from xcat3.plugins import utils as plugin_utils

CONF = cfg.CONF


class UbuntuInterface(base.BaseOSImage):
    """Interface for hardware control actions."""
    TMPL_DIR = os.path.abspath(os.path.dirname(__file__))

    def _get_pkg_list(self):
        """Return pkg list form pkg template"""
        with open(os.path.join(self.TMPL_DIR, 'compute.pkglist')) as f:
            pkgs = f.read()
        pkgs = pkgs.replace('\n', ' ')
        return pkgs

    def build_os_boot_str(self, node, osimage):
        """Generate command line string for specific os image

        :param node: the node to act on.
        :param osimage: osimage object.
        :returns command line string for os repo
        """
        opts = []
        opts.append('url=http://%s/install/autoinst/'
                    '%s' % (CONF.conductor.host_ip,node.name))
        opts.append('live-installer/net-image=http://%s/install/%s/install/'
                    'filesystem.squashfs' %(CONF.conductor.host_ip,
                                            plugin_utils.get_mirror(osimage)))
        opts.append('netcfg/choose_interface=%s' % node.mac)
        opts.append('mirror/http/hostname=%s' % CONF.conductor.host_ip)
        return ' '.join(opts)
