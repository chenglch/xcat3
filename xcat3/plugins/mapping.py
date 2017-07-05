from oslo_log import log
from xcat3.common import exception
from xcat3.plugins.control import ipmi
from xcat3.plugins.control import ssh
from xcat3.plugins.boot import petitboot
from xcat3.plugins.boot import pxe
from xcat3.plugins.osimage import base as os_base
from xcat3.plugins.osimage.ubuntu import ubuntu
from xcat3.plugins.osimage.redhat import redhat

LOG = log.getLogger(__name__)


class PluginMap(object):
    control_map = dict()
    control_map['ipmi'] = ipmi.IPMIPlugin()
    control_map['kvm'] = ssh.SSHControl()
    boot_map = dict()
    boot_map['pxe'] = pxe.PXEBoot()
    boot_map['petitboot'] = petitboot.Petitboot()
    os_map = dict()
    os_map['base'] = os_base.BaseOSImage()
    os_map['ubuntu'] = ubuntu.UbuntuInterface()
    os_map['rhels'] = redhat.RedhatInterface()

    @classmethod
    def get_control_plugin(cls, node):
        control_plugin = cls.control_map.get(node.mgt)
        if control_plugin is None:
            raise exception.PluginNotFound(name=node.mgt)
        return control_plugin

    @classmethod
    def get_boot_plugin(cls, node):
        boot_plugin = cls.boot_map.get(node.netboot)
        if boot_plugin is None:
            raise exception.PluginNotFound(name=node.netboot)
        return boot_plugin

    @classmethod
    def get_osimage_plugin(cls, osimage):
        os_plugin = cls.os_map.get(os_base.get_plugin_name(osimage))
        if os_plugin is None:
            raise exception.PluginNotFound(name=osimage.name)
        return os_plugin
