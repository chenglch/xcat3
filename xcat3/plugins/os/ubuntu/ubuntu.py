# coding=utf-8

import abc
import os
import six
from oslo_config import cfg

from xcat3.common import utils
from xcat3.plugins.os import base
from xcat3.plugins import utils as plugin_utils

CONF = cfg.CONF


class UbuntuInterface(base.OSImageInterface):
    """Interface for hardware control actions."""
    TMPL_DIR = os.path.abspath(os.path.dirname(__file__))

    def validate(self, node):
        """validate the specific attribute

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        pass

    def render(self, node, osimage):
        """Render kickstart template file

        :param node: the node to act on.
        :param osimage: osimage object.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        with open(os.path.join(self.TMPL_DIR, 'compute.pkglist')) as f:
            pkgs = f.read()
        pkgs = pkgs.replace('\n', ' ')
        opts = {'kcmdline': '', 'host_ip': CONF.conductor.host_ip,
                'install': '/install',
                'timezone': 'US/Eastern', 'pkg_list': pkgs,
                'mirror': '%s%s/%s' % (osimage.distro, osimage.ver,
                                       osimage.arch),
                'password': '$6$aUIiJMOg$E4I3hIWzq4eFeIx5zZVtWD.cnDrZs2vJycn4UWPhMcj4JpJPv5wSFEA2HTrVLD5femgQ.kWKQHgzhlKBPDDLH/',
                'api_ip': CONF.api.host_ip,
                'api_port': CONF.api.port,
                'node': node.name,
                }
        template = os.path.join(self.TMPL_DIR, 'compute.tmpl')
        cfg = utils.render_template(template, opts)
        node_tmpl = os.path.join(base.AUTOINST_DIR, node.name)
        utils.write_to_file(node_tmpl, cfg)

        late_script = os.path.join(base.INST_SCRIPTS_DIR, 'post.py')
        ln_late_script = os.path.join(base.INST_SCRIPTS_DIR,
                                      '%s.py' % node.name)
        relative_source_path = os.path.relpath(late_script,
                                               os.path.dirname(ln_late_script))
        utils.create_link_without_raise(relative_source_path, ln_late_script)
