def get_mac_addresses(node):
    """Get all MAC addresses for the nics belonging to this node.

    :param node: the node to act on.
    :returns: A list of MAC addresses in the format xx:xx:xx:xx:xx:xx.
    """
    return [p['mac'] for p in node.nics_info['nics']]