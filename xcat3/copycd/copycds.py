# coding=utf-8

from __future__ import print_function

import os
from oslo_config import cfg

from xcat3.common import exception
from xcat3.common import utils
from xcat3.copycd import base
from xcat3.copycd import cache
from xcat3.common.i18n import _, _LE, _LI, _LW
from oslo_log import log
LOG = log.getLogger(__name__)

CONF = cfg.CONF


def create(iso, image=None, install_dir=None, upload=True):
    if not os.path.isfile(iso) or not os.access(iso, os.R_OK):
        raise exception.InvalidFile(name=iso)
    if not image:
        image = os.path.splitext(os.path.basename(iso))[0]
    if not install_dir:
        install_dir = CONF.deploy.install_dir
    with utils.tempdir() as mntdir:
        # tempdir = os.path.join(CONF.tempdir, 'copycds')
        mount_args = ['-t', 'udf,iso9660', '-o', 'ro,loop']
        sub_classes = base.get_subclasses(base.Image)
        LOG.info(_LI("Mounting iso from %(iso)s to %(path)s "),
                     {'iso': iso, 'path': mntdir})
        utils.mount(iso, mntdir, *mount_args)
        for image_class in sub_classes:
            image_obj = image_class(mntdir, install_dir, image)
            image_info = image_obj.parse_info()
            if not image_info:
                continue
            LOG.info(_LI("Copycd is running for iso %(iso)s"), {'iso': iso})
            image_obj.copycd(image_info)
            cache.backup_iso(iso, install_dir, image)
            if upload:
                image_obj.upload(image_info, os.path.basename(iso))
        utils.umount(mntdir)


def delete(image):
    print (image)
