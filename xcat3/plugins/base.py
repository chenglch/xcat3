import abc
import six

@six.add_metaclass(abc.ABCMeta)
class BaseInterface(object):
    @abc.abstractmethod
    def validate(self, node):
        """Validate the plugin-specific Node deployment info.

        This method is often executed synchronously in API requests, so it
        should not conduct long-running checks.

        :param node: the node to act on.
        :raises: InvalidParameterValue on malformed parameter(s)
        :raises: MissingParameterValue on missing parameter(s)
        """