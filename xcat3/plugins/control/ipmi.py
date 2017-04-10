# coding=utf-8

from oslo_log import log
from xcat3.plugins.control import base
from xcat3.common import exception
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.common import states
from xcat3.common import boot_device

LOG = log.getLogger(__name__)


class IPMIPlugin(base.ControlInterface):
    def validate(self, node):
        """check the ipmi specific attributes"""
        # TODO
        bmc_address = node.control_info.get('bmc_address')
        bmc_username = node.control_info.get('bmc_username')
        if not bmc_address:
            raise exception.MissingParameterValue(
                _("IPMI address was not specified."))
        if not bmc_username:
            raise exception.MissingParameterValue(
                _("IPMI username was not specified."))

    def get_power_state(self, node):
        """Return the power state of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :returns: a power state.
        """
        return states.POWER_ON

    def set_power_state(self, node, power_state):
        """Set the power state of the node's node.

        :param node: the node to act on.
        :param power_state: Any power state.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        LOG.info("RPC set power state called for nodes %(node)s. "
                 "The desired new state is %(target)s.",
                 {'node': node.name, 'target': power_state})
        # Node(chenglch): Just for test
        if node.name == 'node1':
            raise exception.InvalidName(name=node.name)

    def get_boot_device(self, node):
        """Return the boot device of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :returns: the boot device
        """
        return boot_device.NET

    def set_boot_device(self, node, boot_device):
        """Set the boot device of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """
        pass

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
