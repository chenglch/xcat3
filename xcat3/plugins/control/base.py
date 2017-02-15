import abc
import six
from xcat3.plugins import base

@six.add_metaclass(abc.ABCMeta)
class ControlInterface(base.BaseInterface):
    """Interface for hardware control actions."""

    @abc.abstractmethod
    def get_power_state(self, node):
        """Return the power state of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :returns: a power state.
        """

    @abc.abstractmethod
    def set_power_state(self, node, power_state):
        """Set the power state of the node's node.

        :param node: the node to act on.
        :param power_state: Any power state from :mod:`ironic.common.states`.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    @abc.abstractmethod
    def reboot(self, node):
        """Perform a hard reboot of the node's node.

        Drivers are expected to properly handle case when node is powered off
        by powering it on.

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        """

    def get_inventory(self, node):
        """Get the inventory information from control module

        :param node: the node to act on.
        """