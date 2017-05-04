import abc
import errno
import os
import socket
import pypureomapi
import subprocess
import six

from oslo_log import log as logging
from oslo_service import loopingcall
from xcat3.db import api as db_api
from xcat3.common import exception
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.common import utils
from xcat3.conf import CONF

LOG = logging.getLogger(__name__)
BASEDIR = os.path.abspath(os.path.dirname(__file__))

@six.add_metaclass(abc.ABCMeta)
class DhcpBase(object):
    def __init__(self):
        self.subnet_opts = []

    @abc.abstractmethod
    def start(self):
        """Enables DHCP for this network."""

    @abc.abstractmethod
    def stop(self):
        """Disable dhcp for this network."""

    @abc.abstractmethod
    def restart(self):
        """Restart dhcp for this network."""

    @abc.abstractmethod
    def status(self):
        """Status of dhcp server"""

    @abc.abstractmethod
    def update_opts(self, names, dhcp_opts):
        """Add node option for dhcp"""

    @abc.abstractmethod
    def add_subnet(self, subnet_opts):
        """Add subnet option for dhcp"""

    @abc.abstractmethod
    def build_conf(self):
        """build configuration file for dhcp"""


class ISCDHCPService(DhcpBase):
    CONF_PATH = '/etc/dhcp/dhcpd.conf'
    PID_PATH = '/var/run/dhcpd.pid'
    LEASE_PATH = '/var/lib/dhcp/dhcpd.leases'
    DHCP_DICT = {'66': 'server.server-name', '67': 'server.filename',
                 '12': 'host-name', '15': 'server.ddns-hostname'}
    dbapi = db_api.get_instance()

    def __init__(self):
        super(ISCDHCPService, self).__init__()
        self.subnet_opts = list()
        self.dhcp_pobj = None
        self.request_map = dict()
        utils.ensure_file(self.LEASE_PATH)

    def start(self):
        """Enables DHCP service."""
        # TODO(chenglch): We do not hope to change the default configuration
        # file but 'apparmor' deny this.

        # args = ['dhcpd', '-user', 'dhcpd', '-group', 'dhcpd', '-f', '-q', '-4',
        #         '-pf', self.PID_PATH, '-cf', self.CONF_PATH, '-d', '-lf',
        #         self.LEASE_PATH]
        args = ['dhcpd', '-user', 'dhcpd', '-group', 'dhcpd', '-f', '-q', '-4',
                '-pf', self.PID_PATH]
        try:
            LOG.info("Execute command %s ." % ' '.join(args))
            self.dhcp_pobj = subprocess.Popen(args, stdout=subprocess.PIPE,
                                              shell=False)
        except OSError as e:
            error = _("%(exec_error)s\n"
                      "Command: %(command)s") % {'exec_error': str(e),
                                                 'command': ' '.join(args)}
            LOG.warning(error)
            raise exception.DHCPProcessError(err=error)

        locals = {'returncode': None, 'errstr': ''}
        try:
            utils.wait_process(self.dhcp_pobj, args, self.status, 10,
                               locals)
        except loopingcall.LoopingCallDone:
            pass

        if locals['returncode'] is not None and locals['returncode'] != 0:
            LOG.error(_LE('Can not start dhcp service due to error '
                          '%(err)s' % {'err': locals['errstr']}))
            self.dhcp_pobj = None

    def restart(self):
        """Restart DHCP service"""
        # NOTE(chenglch): Seems isc-dhcp-server do not support HUP reload,
        # just stop and start again.
        self.stop()
        self.start()

    def stop(self):
        """Disable DHCP service"""
        if self.dhcp_pobj:
            self.dhcp_pobj.terminate()
            pid = self.dhcp_pobj.pid
            self.dhcp_pobj = None
        else:
            if not os.path.isfile(self.PID_PATH) or not os.access(
                    self.PID_PATH, os.R_OK):
                error = _("Could not access %s, maybe dhcpd prcess is not "
                          "started." % self.PID_PATH)
                LOG.warning(error)
                return

            with open(self.PID_PATH) as f:
                try:
                    pid = int(f.read())
                except ValueError:
                    return

        utils.kill_child_process(pid, 5)

    def status(self):
        try:
            pypureomapi.Omapi(CONF.network.omapi_server,
                              CONF.network.omapi_port, 'xcat_key',
                              CONF.network.omapi_secret)
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                return False
            raise e

        return True

    def get_subnet_opts(self):
        return self.subnet_opts

    @classmethod
    def _build_supersede(cls, opts):
        """Generate dhop configuration content from dhcp option dict"""
        statements = []
        opt = opts.pop('67')
        if opt and type(opt) == dict:
            conf = str()
            first = True
            for k, v in six.iteritems(opt):
                if first:
                    conf += 'if option vendor-class-identifier = "%s" ' \
                            '\t{\n  \tsupersede server.filename = "%s";' \
                            '\n\t}' % (k, v)
                    first = False
                elif k != 'other':
                    conf += '\telse if option vendor-class-identifier = "%s"' \
                            ' \t{\n  \tsupersede server.filename = "%s";' \
                            '\n\t} ' % (k, v)
                else:
                    conf += ' else { \n\t  supersede server.filename = "%s";' \
                            '\n\t} ' % v
            statements.append(conf)
        elif opt:
            conf = 'supersede %s = "%s";' % (cls.DHCP_DICT.get('67'), opt)
            statements.append(conf)

        for k, v in six.iteritems(opts):
            conf = '\tsupersede %s = "%s";' % (cls.DHCP_DICT.get(k), v)
            statements.append(conf)
            if k == '66':
                conf = '\tsupersede server.next-server %s;' % v
                statements.append(conf)

        return '\n'.join(statements)

    @classmethod
    def update_opts(cls, context, op, names, dhcp_opts):
        """Store the configuration options node_opts as dict"""
        node_opts = {}
        if op == 'add':
            template = os.path.join(BASEDIR, 'dhcp_node.template')
            for name in names:
                opts = dhcp_opts[name]
                config = {}
                config['ip'] = opts.pop('ip')
                config['mac'] = opts.pop('mac')
                config['hostname'] = opts.pop('hostname')
                config['statements'] = cls._build_supersede(opts)
                config['content'] = utils.render_template(template, config)
                node_opts[name] = config
            cls.dbapi.save_or_update_dhcp(names, node_opts)
        elif op == 'remove':
            cls.dbapi.destroy_dhcp(names)

    def add_subnet(self, subnet_opts):
        self.subnet_opts.append(subnet_opts)

    def clear_subnet(self):
        self.subnet_opts = list()

    def _build_subnet_cfg(self):
        template = os.path.join(BASEDIR, 'dhcp_subnet.template')
        cfgs = []
        for opts in self.subnet_opts:
            cfg = utils.render_template(template, opts)
            cfgs.append(cfg)
        return '\n'.join(cfgs)

    def _global_cfg(self):
        template = os.path.join(BASEDIR, 'dhcp_global.template')
        opts = {'omapi_secret': CONF.network.omapi_secret,
                'omapi_port': CONF.network.omapi_port}
        return utils.render_template(template, opts)

    def build_conf(self):
        node_cfgs = []
        node_opts = self.dbapi.get_dhcp_list()
        for opt in node_opts:
            content = opt['opts']['content']
            node_cfgs.append(content)
        cfg = '%(global_cfg)s%(subnet_cfg)s\n%(node_cfg)s' % {
            'global_cfg': self._global_cfg(),
            'subnet_cfg': self._build_subnet_cfg(),
            'node_cfg': '\n'.join(node_cfgs)}
        utils.write_to_file(self.CONF_PATH, cfg)
        # clean up the lease file, as restart dhcp will generate it again.
        with open(self.LEASE_PATH, 'w') as f:
            f.truncate()
        os.chown(self.LEASE_PATH, 0, 0)
