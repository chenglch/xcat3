from oslo_log import log
from xcat3.common import exception
from xcat3.plugins.control import ipmi
from xcat3.plugins.control import ssh

LOG = log.getLogger(__name__)

control_map = dict()
control_map['ipmi'] = ipmi.IPMIPlugin()
control_map['kvm'] = ssh.SSHControl()

boot_map = dict()
os_map = dict()


def get_control_plugin(node):
    control_plugin = control_map.get(node.mgt)
    if not control_plugin:
        raise exception.PluginNotFound(name=node.mgt)
    return control_plugin



