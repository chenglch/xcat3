# coding=utf-8

import os
import shutil
from oslo_config import cfg
from oslo_concurrency import lockutils
from xcat3.plugins.os import base

CONF = cfg.CONF


class RedhatInterface(base.BaseOSImage):
    """Interface for hardware control actions."""
    TMPL_DIR = os.path.abspath(os.path.dirname(__file__))

    @lockutils.synchronized('xcat3-scripts.lock', external=True)
    def _ensure(self):
        shutil.copy(os.path.join(base.SCRIPTS_DIR, 'pre.rhels.sh'),
                    base.INST_SCRIPTS_DIR)

    def _get_pkg_list(self):
        """Return pkg list form pkg template"""
        with open(os.path.join(self.TMPL_DIR, 'compute.pkglist')) as f:
            return f.read()

    def build_os_boot_str(self, node, osimage):
        """Generate command line string for specific os image

        :param node: the node to act on.
        :param osimage: osimage object.
        :returns command line string for os repo
        """
        opts = []
        mirror = '%s%s/%s' % (osimage.distro, osimage.ver, osimage.arch)
        opts.append('inst.ks=http://%s/install/autoinst/'
                    '%s' % (CONF.conductor.host_ip, node.name))
        opts.append('inst.repo=http://%s/install/%s' % (CONF.conductor.host_ip,
                                                        mirror))
        return ' '.join(opts)
