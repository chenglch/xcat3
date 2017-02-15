from oslo_log import log
from xcat3.plugins.control import base
from xcat3.common import exception

LOG = log.getLogger(__name__)


class IPMIPlugin(base.ControlInterface):
    def validate(self, node):
        """check the attribute of ipmi_address, ipmi_user"""
        pass

    def get_power_state(self, node):
        """Return the power state of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :returns: a power state.
        """
        return 'on'

    def set_power_state(self, node, power_state):
        """Set the power state of the node's node.

        :param node: the node to act on.
        :param power_state: Any power state.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        LOG.info("RPC change_power_state called for nodes %(node)s. "
                 "The desired new state is %(target)s.",
                 {'node': node.name, 'target': power_state})
        # Node(chenglch): Just for test
        if node.name == 'node1':
            raise exception.InvalidName(name=node.name)

    def reboot(self, node):
        """Perform a hard reboot of the node's node.

        Drivers are expected to properly handle case when node is powered off
        by powering it on.

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        pass

    def get_inventory(self, node):
        """Get the inventory information from control module

        :param node: the node to act on.
        """
        pass
