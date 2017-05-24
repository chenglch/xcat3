# coding=utf-8

import abc
import os
import six
import shutil
from oslo_config import cfg

from xcat3.common import utils
from xcat3.plugins import base
from xcat3.plugins import utils as plugin_utils
from oslo_utils import fileutils
from oslo_concurrency import lockutils

CONF = cfg.CONF

os_dict = {'Ubuntu-Server': 'ubuntu',
           'rhels': 'rhels'}

AUTOINST_DIR = os.path.join(CONF.deploy.install_dir, 'autoinst')
INST_SCRIPTS_DIR = os.path.join(CONF.deploy.install_dir, 'scripts')
BACKUP_ISO_DIR = os.path.join(CONF.deploy.install_dir, 'iso')
BASEDIR = os.path.abspath(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.join(BASEDIR, 'scripts')


def get_plugin_name(osimage):
    return 'base' if osimage == 'base' else os_dict.get(osimage.distro)


@six.add_metaclass(abc.ABCMeta)
class OSImageInterface(base.BaseInterface):
    """Interface for hardware control actions."""

    @abc.abstractmethod
    def _get_pkg_list(self):
        """Return pkg list form pkg template"""

    @abc.abstractmethod
    def validate(self, node):
        """validate the specific attribute

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        pass

    @abc.abstractmethod
    def build_template(self, node, osimage):
        """Render kickstart template file

        :param node: the node to act on.
        :param osimage: osimage object.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    @abc.abstractmethod
    def clean(self, node):
        """Clean up the files while deploying"""

    @abc.abstractmethod
    def build_os_boot_str(self, node, osimage):
        """Generate command line string for specific os image

        :param node: the node to act on.
        :param osimage: osimage object.
        :returns command line string for os repo
        """

class BaseOSImage(OSImageInterface):
    """Interface for hardware control actions."""

    @lockutils.synchronized('xcat3-scripts.lock', external=True)
    def _ensure(self):
        if os.path.exists(os.path.join(INST_SCRIPTS_DIR, 'post.py')):
            return
        fileutils.ensure_tree(AUTOINST_DIR)
        fileutils.ensure_tree(INST_SCRIPTS_DIR)
        fileutils.ensure_tree(BACKUP_ISO_DIR)
        shutil.copy(os.path.join(SCRIPTS_DIR, 'post.py'), INST_SCRIPTS_DIR)
        shutil.copy(os.path.join(SCRIPTS_DIR, 'getinstdisk.sh'),
                    INST_SCRIPTS_DIR)

    def __init__(self):
        self._ensure()

    def validate(self, node):
        """validate the specific attribute

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        pass

    def _get_pkg_list(self):
        """Return pkg list form pkg template"""
        pass

    def build_template(self, node, osimage):
        """Render kickstart template file

        :param node: the node to act on.
        :param osimage: osimage object.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        opts = {'host_ip': CONF.conductor.host_ip,
                'mac': node.mac,
                'install_dir': '/install',
                'timezone': 'US/Eastern', 'pkg_list': self._get_pkg_list(),
                'mirror': '%s%s/%s' % (osimage.distro, osimage.ver,
                                       osimage.arch),
                'password': '$6$aUIiJMOg$E4I3hIWzq4eFeIx5zZVtWD.cnDrZs2vJycn4UWPhMcj4JpJPv5wSFEA2HTrVLD5femgQ.kWKQHgzhlKBPDDLH/',
                'api_ip': CONF.api.host_ip,
                'api_port': CONF.api.port,
                'node': node.name,
                }
        template = os.path.join(self.TMPL_DIR, 'compute.tmpl')
        cfg = utils.render_template(template, opts)
        node_tmpl = os.path.join(AUTOINST_DIR, node.name)
        utils.write_to_file(node_tmpl, cfg)

    def clean(self, node):
        """Clean up the files while deploying"""
        utils.unlink_without_raise(os.path.join(AUTOINST_DIR, node.name))

    def build_os_boot_str(self, node, osimage):
        pass
