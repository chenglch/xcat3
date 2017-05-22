# coding=utf-8

from __future__ import print_function

import os
import shutil

from oslo_config import cfg
from oslo_utils import fileutils

from xcat3.common import exception
from xcat3.common import utils
from xcat3.copycd import base

CONF = cfg.CONF


def _backup_iso(iso, install_dir, image):
    iso_dir = os.path.join(install_dir, 'iso')
    fileutils.ensure_tree(iso_dir)
    backup_path = os.path.join(iso_dir, '%s.iso' % image)
    if not os.path.exists(backup_path):
        print(_("Copy iso from %(src)s to %(dst)s" % {'src': iso,
                                                      'dst': backup_path}))
        shutil.copy(iso, backup_path)
    return os.path.relpath(iso_dir,install_dir)


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
        utils.mount(iso, mntdir, *mount_args)
        for image_class in sub_classes:
            image_obj = image_class(mntdir, install_dir, image)
            image_info = image_obj.parse_info()
            if not image_info:
                continue
            image_obj.copycd(image_info)
            backup_path = _backup_iso(iso, install_dir, image)
            if upload:
                image_obj.upload(image_info, backup_path)
        utils.umount(mntdir)


def delete(image):
    print (image)
