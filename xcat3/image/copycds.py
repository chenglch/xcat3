# coding=utf-8

from __future__ import print_function

import os
from oslo_config import cfg
from xcat3.common import exception
from xcat3.common.i18n import _
from xcat3.common import utils

from xcat3.image.copycd import base

CONF = cfg.CONF


def create(iso, image=None, install_dir=None):
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
            image_obj.upload(image_info)
        utils.umount(mntdir)


def upload(image):
    print (image)


def delete(image):
    print (image)
