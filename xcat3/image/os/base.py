import abc
import errno
import glob
import inspect
import os
import six
import subprocess
import time

from oslo_utils import importutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall

from xcat3.common.i18n import _
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

    @abc.abstractmethod
    def parse_info(self):
        """Parse the product version and arch information"""

    @abc.abstractmethod
    def copycd(self, disk_info):
        """Create netboot image at install directory"""