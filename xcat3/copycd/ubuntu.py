# coding=utf-8

import os
from oslo_log import log
from oslo_config import cfg

from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.copycd import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF
PLUGIN_LOG = "Ubuntu:"


class UbuntuImage(base.Image):
    def __init__(self, mnt_dir, install_dir, name):
        super(UbuntuImage, self).__init__(mnt_dir, install_dir, name)

    def parse_info(self):
        info = dict()
        dist_info_file = os.path.join(self.mnt_dir, '.disk', 'info')
        if not os.path.isfile(dist_info_file) or not os.access(
                dist_info_file, os.R_OK):
            LOG.debug(_("%(plugin)sCan not access path %(path)s"),
                      {'plugin': PLUGIN_LOG, 'path': dist_info_file})
            return None

        with open(dist_info_file) as f:
            line = f.read()
            vals = line.split(' ')
            if len(vals) < 7:
                LOG.debug(_("%(plugin)sDisk info do not match."),
                          {'plugin': PLUGIN_LOG})
                return None
            info['product'] = vals[0]
            info['version'] = vals[1]
            info['arch'] = vals[6]

        if not info['product'] in ['Ubuntu', 'Ubuntu-Server']:
            LOG.debug(_("%(plugin)sNot ubuntu product."),
                      {'plugin': PLUGIN_LOG})
            return None

        info['arch'] = vals[7] if len(vals) >= 8 else None
        if not info['arch']:
            return None
        if info['arch'] == 'amd64':
            info['arch'] = 'x86_64'

        return info

    def _get_kernel_path(self, dist_info):
        return os.path.join(self.dist_path, 'install', 'vmlinuz')

    def _get_initrd_path(self, dist_info):
        arch = dist_info['arch'] if dist_info['arch'] != 'x86_64' else 'amd64'
        return os.path.join(self.dist_path, 'install', 'netboot',
                            'ubuntu-installer', arch, 'initrd.gz')
