from oslo_log import log
from xcat3.common import exception
from xcat3.plugins.control import ipmi

LOG = log.getLogger(__name__)

plugin_map = dict()
plugin_map['ipmi'] = ipmi.IPMIPlugin()


def get_plugin(node):
    control_plugin = plugin_map.get(node.mgt)
    os_plugin = None
    boot_plugin = None
    if not control_plugin:
        raise exception.PluginNotFound(name=node.mgt)
    return control_plugin, os_plugin, boot_plugin



