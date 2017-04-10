# coding=utf-8

import os
from oslo_log import log
from oslo_config import cfg

import shutil

from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.image.os import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF
PLUGIN_LOG = "Ubuntu:"


class UbuntuImage(base.Image):
    def __init__(self, mnt_dir, install_dir, name):
        super(UbuntuImage, self).__init__(mnt_dir, install_dir, name)

    def parse_info(self):
        info = dict()
        disk_info_file = os.path.join(self.mnt_dir, '.disk', 'info')
        if not os.path.isfile(disk_info_file) or not os.access(
                disk_info_file, os.R_OK):
            LOG.debug(_("%(plugin)sCan not access path %(path)s"),
                      {'plugin': PLUGIN_LOG, 'path': disk_info_file})
            return None

        with open(disk_info_file) as f:
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

    def copycd(self, disk_info):
        dist_name = "%s%s" % (disk_info['product'], disk_info['version'])
        dist_path = os.path.join(self.install_dir, dist_name,
                                 disk_info['arch'])
        self._cpio(dist_path)
        self._copy_tftp(dist_path, disk_info)

    def _copy_netboot_initrd(self, dist_path, disk_info):
        dist_name = "%s%s" % (disk_info['product'], disk_info['version'])
        arch = disk_info['arch']
        if arch == 'x86_64':
            arch = 'amd64'
        install_initrd = os.path.join(dist_path, 'install', 'netboot',
                                      'ubuntu-installer', arch, 'initrd.gz')

        tftp_initrd = os.path.join(CONF.deploy.tftp_dir, 'images', dist_name,
                                   disk_info['arch'], 'initrd.img')
        shutil.copy(install_initrd, tftp_initrd)
        # copyAndAddCustomizations($initrdpath, "$tftppath/initrd.img");
