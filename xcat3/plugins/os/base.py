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

os_dict = {'Ubuntu-Server': 'ubuntu'}
AUTOINST_DIR = os.path.join(CONF.deploy.install_dir, 'autoinst')
INST_SCRIPTS_DIR = os.path.join(CONF.deploy.install_dir, 'scripts')
BASEDIR = os.path.abspath(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.join(BASEDIR, 'scripts')


def get_plugin_name(osimage):
    return os_dict.get(osimage.distro)


@six.add_metaclass(abc.ABCMeta)
class OSImageInterface(base.BaseInterface):
    """Interface for hardware control actions."""

    @lockutils.synchronized('xcat3-scripts', external=True)
    def _ensure(self):
        if os.path.exists(os.path.join(INST_SCRIPTS_DIR, 'post.py')):
            return
        fileutils.ensure_tree(AUTOINST_DIR)
        fileutils.ensure_tree(INST_SCRIPTS_DIR)
        shutil.copy(os.path.join(SCRIPTS_DIR, 'post.py'), INST_SCRIPTS_DIR)
        shutil.copy(os.path.join(SCRIPTS_DIR, 'getinstdisk.sh'),
                    INST_SCRIPTS_DIR)

    def __init__(self):
        self._ensure()

    @abc.abstractmethod
    def validate(self, node):
        """validate the specific attribute

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    @abc.abstractmethod
    def render(self, node, osimage):
        """Render kickstart template file

        :param node: the node to act on.
        :param osimage: osimage object.
        :raises: MissingParameterValue if a required parameter is missing.
        """
