import ipaddress
import netaddr
import netifaces

from oslo_log import log
from xcat3.common.i18n import _, _LE, _LI, _LW

LOG = log.getLogger(__name__)


def get_cidr(network, netmask):
    return "%s/%s" % (network, netaddr.IPAddress(netmask).netmask_bits())


class IPWrapper(object):
    def get_device_by_ip(self, ip):
        if not ip:
            return

        for device in self.get_devices():
            if device.device_has_ip(ip):
                return device

    def get_devices(self):
        try:
            return [IPDevice(iface) for iface in netifaces.interfaces()]
        except (OSError, MemoryError):
            LOG.error(_LE("Failed to get network interfaces."))
            return []

    def get_devices_in_network(self, network, netmask):
        devices = []
        for ip_dev in self.get_devices():
            if ip_dev.device_in_network(network, netmask):
                devices.append(ip_dev)
        return devices

    def get_net_bits(self, netmask):
        return netaddr.IPAddress(netmask).netmask_bits()


class IPDevice(object):
    def __init__(self, name):
        self.name = name
        self.link = IPLink(self)

    def read_ifaddresses(self):
        try:
            device_addresses = netifaces.ifaddresses(self.name)
        except ValueError:
            LOG.error(_LE("The device does not exist on the system: %s."),
                      self.name)
            return
        except OSError:
            LOG.error(_LE("Failed to get interface addresses: %s."),
                      self.name)
            return
        return device_addresses

    def device_has_ip(self, ip):
        device_addresses = self.read_ifaddresses()
        if device_addresses is None:
            return False

        addresses = [ip_addr['addr'] for ip_addr in
                     device_addresses.get(netifaces.AF_INET, [])]
        return ip in addresses

    def devices_ips(self):
        device_addresses = self.read_ifaddresses()
        if device_addresses is None:
            return None
        addresses = [ip_addr['addr'] for ip_addr in
                     device_addresses.get(netifaces.AF_INET, [])]
        return addresses

    def address_in_network(self, ip, network, netmask):
        "Is an ip address in a network"
        cidr = get_cidr(network, netmask)
        if ipaddress.ip_address(unicode(ip)) in ipaddress.ip_network(
                unicode(cidr)):
            return True
        return False

    def device_in_network(self, network, netmask):
        addresses = self.devices_ips()
        for addr in addresses:
            if self.address_in_network(addr, network, netmask):
                return True
        return False


class IPLink(object):
    def __init__(self, parent):
        self._parent = parent

    @property
    def address(self):
        device_addresses = self._parent.read_ifaddresses()
        if device_addresses is None:
            return False
        return [eth_addr['addr'] for eth_addr in
                device_addresses.get(netifaces.AF_LINK, [])]
