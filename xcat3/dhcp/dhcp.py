import abc
import os
import six
import shutil

from oslo_utils import fileutils
from oslo_log import log as logging
from xcat3.common import exception
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.common import states
from xcat3.common import utils
from xcat3.conf import CONF

LOG = logging.getLogger(__name__)
BASEDIR = os.path.abspath(os.path.dirname(__file__))


@six.add_metaclass(abc.ABCMeta)
class DhcpBase(object):
    def __init__(self):
        self.subnet_opts = []
        self.node_opts = []

    @abc.abstractmethod
    def enable(self):
        """Enables DHCP for this network."""

    @abc.abstractmethod
    def disable(self):
        """Disable dhcp for this network."""

    @abc.abstractmethod
    def add_node(self, node_opts):
        """Add node option for dhcp"""

    @abc.abstractmethod
    def add_subnet(self, subnet_opts):
        """Add subnet option for dhcp"""

    @abc.abstractmethod
    def build_conf(self):
        """build configuration file for dhcp"""


class ISCDHCPService(DhcpBase):
    CONF_PATH = '/etc/dhcp/dhcpd.conf'
    LEASES_PATH = '/var/lib/dhcp/dhcpd.leases'

    def __init__(self):
        super(ISCDHCPService, self).__init__()
        self.subnet_opts = list()
        self.node_opts = list()
        # fileutils.ensure_tree(self.LEASES_PATH, mode=0o755)

    def enable(self):
        """Enables DHCP service."""
        args = ['/usr/sbin/service', 'isc-dhcp-server', 'start']

        try:
            utils.execute(*args)
        except (OSError, ValueError) as e:
            error = _("%(exec_error)s\n"
                      "Command: %(command)s") % {'exec_error': str(e),
                                                 'command': ' '.join(args)}
            LOG.warning(error)
            raise exception.DHCPProcessError(err=error)

    def restart(self):
        args = ['/usr/sbin/service', 'isc-dhcp-server', 'restart']

        try:
            utils.execute(*args)
        except (OSError, ValueError) as e:
            error = _("%(exec_error)s\n"
                      "Command: %(command)s") % {'exec_error': str(e),
                                                 'command': ' '.join(args)}
            LOG.warning(error)
            raise exception.DHCPProcessError(err=error)

    def disable(self, retain_port=False):
        """Disable DHCP service"""

        args = ['/usr/sbin/service', 'isc-dhcp-server', 'stop']
        # args = ['dhcpd', '-user', 'dhcpd', '-group', 'dhcpd', '-f', '-q', '-4', '-pf', ''isc-dhcp-server', 'stop']
        try:
            utils.execute(args)
        except (OSError, ValueError) as e:
            error = _("%(exec_error)s\n"
                      "Command: %(command)s") % {'exec_error': str(e),
                                                 'command': ' '.join(args)}
            LOG.warning(error)

    def add_node(self, node_opts):
        pass

    def add_subnet(self, subnet_opts):
        self.subnet_opts.append(subnet_opts)

    def _generate_subnet_cfg(self, opts):
        template = os.path.join(BASEDIR, 'dhcp_subnet.template')
        cfg = utils.render_template(template, opts)
        return cfg

    def _global_cfg(self):
        cfg_file = os.path.join(BASEDIR, 'dhcp_global.template')
        with open(cfg_file, 'r') as f:
            return f.read()

    def build_conf(self):
        cfg = self._global_cfg()
        for opts in self.subnet_opts:
            cfg = '%s\n%s' % (cfg, self._generate_subnet_cfg(opts))
        utils.write_to_file(self.CONF_PATH, cfg)
