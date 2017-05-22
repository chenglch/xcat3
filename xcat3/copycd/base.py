# coding=utf-8

from __future__ import print_function

import abc
import errno
import glob
import inspect
import os
import select
import six
import subprocess

from oslo_utils import importutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import fileutils
import shutil

from xcat3.common.i18n import _
from xcat3.common import exception
from xcat3.common import utils
from xcat3 import objects

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def get_modules():
    modules = glob.glob(os.path.join(os.path.dirname(__file__), '*.py'))
    modules = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f)]
    modules = [f for f in modules if not f.startswith('__') and f !=
               os.path.splitext(os.path.basename(__file__))[0]]
    return modules


def get_subclasses(clazz):
    modules = get_modules()
    classes = []
    for module in modules:
        module = importutils.try_import('xcat3.copycd.%s' % module)
        for name, cls in inspect.getmembers(module):
            if inspect.isclass(cls) and issubclass(cls, clazz):
                classes.append(cls)
    return classes


@six.add_metaclass(abc.ABCMeta)
class Image(object):
    def __init__(self, mnt_dir, install_dir, name):
        self.mnt_dir = mnt_dir
        self.install_dir = install_dir
        self.name = name
        self.dist_name = None
        self.dist_path = None

    def _cpio(self, dist_path):
        try:
            os.makedirs(dist_path, 0755, )
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dist_path):
                pass
            else:
                raise

        cur_dir = os.getcwd()
        os.chdir(self.mnt_dir)
        args1 = ['find', '.']
        args2 = ['cpio', '-vdump', dist_path]
        print(_("Copying image from %(mnt_dir)s to %(dist_path)s, this may "
                "takes a few minutes, please wait...") %
              {'mnt_dir': self.mnt_dir, 'dist_path': dist_path})
        process_find = subprocess.Popen(args1, stdout=subprocess.PIPE,
                                        shell=False)
        # check the find output
        while not select.select([process_find.stdout, ], [], [], 0.5)[0]:
            pass
        process_cpio = subprocess.Popen(args2, stdin=process_find.stdout,
                                        stdout=utils.DEVNULL,
                                        stderr=utils.DEVNULL,
                                        shell=False)
        locals = {'returncode': None, 'errstr': ''}
        try:
            utils.wait_process(process_cpio, args2, None, 300, locals)
        except loopingcall.LoopingCallDone:
            pass

        if locals['returncode'] is None or locals['returncode'] != 0:
            raise

        os.chdir(cur_dir)

    def _copy_to_tftp(self, kernel_path, initrd_path, tftp_kernel_path,
                      tftp_initrd_path):
        fileutils.ensure_tree(tftp_kernel_path)
        fileutils.ensure_tree(tftp_initrd_path)
        shutil.copy(kernel_path, os.path.join(tftp_kernel_path, 'vmlinuz'))
        shutil.copy(initrd_path, os.path.join(tftp_initrd_path, 'initrd.img'))

    @abc.abstractmethod
    def parse_info(self):
        """Parse the product version and arch information"""

    @abc.abstractmethod
    def _get_kernel_path(self, dist_info):
        """Return the dist kernel path in install directory"""

    @abc.abstractmethod
    def _get_kernel_path(self, dist_info):
        """Return the dist initrd path in install directory"""

    def copycd(self, dist_info):
        """Create netboot image at install directory"""
        self.dist_name = "%s%s" % (dist_info['product'], dist_info['version'])
        self.dist_path = os.path.join(self.install_dir, self.dist_name,
                                      dist_info['arch'])
        self._cpio(self.dist_path)
        if dist_info['arch'] == 'x86_64':
            kernel_path = self._get_kernel_path(dist_info)
            initrd_path = self._get_initrd_path(dist_info)

            tftp_initrd_path = os.path.join(CONF.deploy.tftp_dir, 'images',
                                            self.dist_name, dist_info['arch'])
            tftp_kernel_path = os.path.join(CONF.deploy.tftp_dir, 'images',
                                            self.dist_name, dist_info['arch'])
            self._copy_to_tftp(kernel_path, initrd_path, tftp_kernel_path,
                               tftp_initrd_path)

    def upload(self, dist_info, backup_path):
        """Upload image information to database"""
        print('Uploading image information...')
        dist_name = "%s%s" % (dist_info['product'], dist_info['version'])
        osimage_name = "%s-%s" % (dist_name, dist_info['arch'])
        try:
            image_obj = objects.OSImage.get_by_name(None, osimage_name)
            image_obj.destroy()
        except exception.OSImageNotFound:
            pass
        image_dict = {"name": osimage_name,
                      "arch": dist_info['arch'],
                      "ver": dist_info['version'],
                      "distro": dist_info['product'],
                      "iso_path": backup_path}

        new_image = objects.OSImage(None, **image_dict)
        new_image.create()
