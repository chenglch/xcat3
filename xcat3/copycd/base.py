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
            raise exception.CommandFailed(
                cmd='cd %s; %s | %s' % (self.mnt_dir,
                                        ' '.join(args1),
                                        ' '.join(args2)))

        os.chdir(cur_dir)

    def _link_to_netboot(self, kernel, initrd, target):
        fileutils.ensure_tree(target)
        netboot_kernel = os.path.join(target, 'vmlinuz')
        netboot_initrd = os.path.join(target, 'initrd.img')
        # create link for netboot
        relative_source_path = os.path.relpath(kernel,
                                               os.path.dirname(netboot_kernel))
        utils.create_link_without_raise(relative_source_path, netboot_kernel)
        relative_source_path = os.path.relpath(initrd,
                                               os.path.dirname(netboot_initrd))
        utils.create_link_without_raise(relative_source_path, netboot_initrd)

    @abc.abstractmethod
    def parse_info(self):
        """Parse the product version and arch information"""

    @abc.abstractmethod
    def _get_kernel_path(self, dist_info):
        """Return the dist kernel path in install directory"""

    @abc.abstractmethod
    def _get_initrd_path(self, dist_info):
        """Return the dist initrd path in install directory"""

    def copycd(self, dist_info):
        """Create netboot image at install directory"""
        self.dist_name = "%s%s" % (dist_info['product'], dist_info['version'])
        self.dist_path = os.path.join(self.install_dir, self.dist_name,
                                      dist_info['arch'])
        self._cpio(self.dist_path)
        kernel_path = self._get_kernel_path(dist_info)
        initrd_path = self._get_initrd_path(dist_info)
        if dist_info['arch'] == 'x86_64':
            target = os.path.join(CONF.deploy.tftp_dir, 'images',
                                  self.dist_name, dist_info['arch'])
        elif dist_info['arch'] == 'ppc64le' or dist_info['arch'] == 'ppc64el':
            target = os.path.join(self.dist_path, 'xcat')
        else:
            msg = _("Unsupported arch %s" % dist_info['arch'])
            raise exception.UnExpectedError(err=msg)
        self._link_to_netboot(kernel_path, initrd_path, target)

    def upload(self, dist_info, path):
        """Upload image information to database"""
        print('Uploading image information...')
        dist_name = "%s%s" % (dist_info['product'], dist_info['version'])
        if self.name is None:
            self.name = "%s-%s" % (dist_name, dist_info['arch'])
        try:
            image_obj = objects.OSImage.get_by_distro_info(None,
                dist_info['product'], dist_info['version'], dist_info['arch'])
            image_obj.name = self.name
            image_obj.orig_name = path
            image_obj.save()
        except exception.OSImageNotFound:
            image_dict = {"name": self.name,
                          "arch": dist_info['arch'],
                          "ver": dist_info['version'],
                          "distro": dist_info['product'],
                          "orig_name": path}

            new_image = objects.OSImage(None, **image_dict)
            new_image.create()
