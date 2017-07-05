# coding=utf-8

import os
from oslo_config import cfg
from xcat3.common import utils

CONF = cfg.CONF


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
        if p.has_key('primary'):
            return p['mac']
    return None


def get_primary_ip_address(node):
    """Get the IP address for installation.

    :param node: the node to act on
    :returns: ip address
    """
    for p in node.nics_info['nics']:
        if p.has_key('primary') and p.has_key('ip'):
            return p['ip']
    return None


def get_mirror(osimage):
    return '%s%s/%s' % (osimage.distro, osimage.ver, osimage.arch)


def get_http_root_for_osimage(osimage):
    return os.path.join(CONF.deploy.install_dir, get_mirror(osimage))


def get_tftp_root_for_osimage(osimage):
    return os.path.join(CONF.deploy.tftp_dir, 'images', get_mirror(osimage))


def get_tftp_root_for_node(node):
    return os.path.join(CONF.deploy.tftp_dir, 'nodes', node.name)


def get_http_root_for_node(node):
    return os.path.join(CONF.deploy.install_dir, 'nodes', node.name)


def get_http_url_for_osimage(osimage):
    return "http://%s/install/%s" % (CONF.conductor.host_ip,
                                     get_mirror(osimage))


def destroy_osimages(osimage):
    """Clean up osimages files

    :param osimage: osimage object.
    """
    tftp_path = get_tftp_root_for_osimage(osimage)
    http_path = get_http_root_for_osimage(osimage)
    iso_path = os.path.join(CONF.deploy.install_dir, 'iso', osimage.orig_name)
    utils.rmtree_without_raise(tftp_path)
    utils.rmtree_without_raise(http_path)
    utils.unlink_without_raise(iso_path)
    # remove the directory if empty
    tftp_dir = os.path.join(CONF.deploy.tftp_dir, 'images',
                            '%s%s' % (osimage.distro, osimage.ver))
    http_dir = os.path.join(CONF.deploy.install_dir,
                            '%s%s' % (osimage.distro, osimage.ver))
    utils.rmdir_without_raise(tftp_dir)
    utils.rmdir_without_raise(http_dir)