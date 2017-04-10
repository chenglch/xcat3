# coding=utf-8

import abc
import errno
import glob
import inspect
import os
import select
import six
import six.moves.urllib.parse as urlparse
import subprocess
import time

from oslo_utils import importutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import fileutils
import shutil

from xcat3.common.i18n import _
from xcat3.common import client as http_client
from xcat3.common import utils

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
        module = importutils.try_import('xcat3.image.os.%s' % module)
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

    def _cpio(self, dist_path):

        def _wait(popen_obj, args, expiration):
            expiration = time.time() + expiration
            while True:
                locals['returncode'] = popen_obj.poll()
                if locals['returncode'] is not None:
                    if locals['returncode'] == 0:
                        raise loopingcall.LoopingCallDone()
                    else:
                        (stdout, stderr) = popen_obj.communicate()
                        locals['errstr'] = _(
                            "Command: %(command)s.\n"
                            "Exit code: %(return_code)s.\n"
                            "Stdout: %(stdout)r\n"
                            "Stderr: %(stderr)r") % {
                               'command': ' '.join(args),
                               'return_code': locals['returncode'],
                               'stdout': stdout,
                               'stderr': stderr}
                        LOG.warning(locals['errstr'])
                        raise loopingcall.LoopingCallDone()

                if (time.time() > expiration):
                    locals['errstr'] = _(
                        "Timeout while waiting for command subprocess "
                        "%(args)s") % {'args': " ".join(args)}
                    LOG.warning(locals['errstr'])
                    raise loopingcall.LoopingCallDone()

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
        print _(
            "Copy image from %(mnt_dir)s to %(dist_path)s, please wait...") % {
                  'mnt_dir': self.mnt_dir, 'dist_path': dist_path}
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
            _wait(process_cpio, args2, 300)
        except loopingcall.LoopingCallDone:
            pass

        if locals['returncode'] is None or locals['returncode'] != 0:
            raise

        os.chdir(cur_dir)

    def _copy_netboot_initrd(self, dist_path, disk_info):
        pass

    def _copy_tftp(self, dist_path, disk_info):
        dist_name = "%s%s" % (disk_info['product'], disk_info['version'])
        install_kernel = os.path.join(dist_path, 'install', 'vmlinuz')
        tftp_dir = os.path.join(CONF.deploy.tftp_dir, 'images', dist_name,
                                disk_info['arch'])
        fileutils.ensure_tree(tftp_dir)
        shutil.copy(install_kernel, tftp_dir)
        self._copy_netboot_initrd(dist_path, disk_info)


    @abc.abstractmethod
    def parse_info(self):
        """Parse the product version and arch information"""

    @abc.abstractmethod
    def copycd(self, disk_info):
        """Create netboot image at install directory"""

    def upload(self, disk_info):
        print 'Uploading image information...'
        dist_name = "%s%s" % (disk_info['product'], disk_info['version'])
        client = http_client.HttpClient()
        url = utils.get_api_url()
        headers = {'Content-Type': 'application/json'}
        image_url = urlparse.urljoin(url, 'osimages')
        data = {"name": "%s-%s" % (dist_name, disk_info['arch']),
                "arch": disk_info['arch'],
                "ver": disk_info['version'],
                "distro": disk_info['product']}
        # delete the image if exists
        try:
            client.delete(urlparse.urljoin(url, 'osimages/%s' % dist_name),
                          headers=headers)
        except Exception:
            pass
        client.post(image_url, headers=headers, body=data)
