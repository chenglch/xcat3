import os
from xcat3.common import utils


def get_mac_addresses(node):
    """Get all MAC addresses for the nics belonging to this node.

    :param node: the node to act on.
    :returns: A list of MAC addresses in the format xx:xx:xx:xx:xx:xx.
    """
    return [p.get('mac') for p in node.nics_info['nics']]


def get_primary_mac_address(node):
    """Get the MAC address for installation.

    :param node: the node to act on
    :returns: mac address in the format xx:xx:xx:xx:xx:xx.
    """
    for p in node.nics_info['nics']:
        if p.get('extra') and p.get('extra').get('primary') and p.get('mac'):
            return p['mac']
    return None


def get_primary_ip_address(node):
    """Get the IP address for installation.

    :param node: the node to act on
    :returns: ip address
    """
    for p in node.nics_info['nics']:
        if p.get('extra') and p.get('extra').get('primary') and p.get('ip'):
            return p['ip']
    return None
