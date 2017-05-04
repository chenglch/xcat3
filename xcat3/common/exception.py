# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""xCAT base exception handling.

SHOULD include dedicated exception logging.

"""

import collections

from oslo_log import log as logging
from oslo_serialization import jsonutils
import six
from six.moves import http_client

from xcat3.common.i18n import _, _LE
from xcat3.conf import CONF

LOG = logging.getLogger(__name__)


def _ensure_exception_kwargs_serializable(exc_class_name, kwargs):
    """Ensure that kwargs are serializable

    Ensure that all kwargs passed to exception constructor can be passed over
    RPC, by trying to convert them to JSON, or, as a last resort, to string.
    If it is not possible, unserializable kwargs will be removed, letting the
    receiver to handle the exception string as it is configured to.

    :param exc_class_name: an XCAT3Exception class name.
    :param kwargs: a dictionary of keyword arguments passed to the exception
        constructor.
    :returns: a dictionary of serializable keyword arguments.
    """
    serializers = [(jsonutils.dumps, _('when converting to JSON')),
                   (six.text_type, _('when converting to string'))]
    exceptions = collections.defaultdict(list)
    serializable_kwargs = {}
    for k, v in kwargs.items():
        for serializer, msg in serializers:
            try:
                serializable_kwargs[k] = serializer(v)
                exceptions.pop(k, None)
                break
            except Exception as e:
                exceptions[k].append(
                    '(%(serializer_type)s) %(e_type)s: %(e_contents)s' %
                    {'serializer_type': msg, 'e_contents': e,
                     'e_type': e.__class__.__name__})
    if exceptions:
        LOG.error(
            _LE("One or more arguments passed to the %(exc_class)s "
                "constructor as kwargs can not be serialized. The serialized "
                "arguments: %(serialized)s. These unserialized kwargs were "
                "dropped because of the exceptions encountered during their "
                "serialization:\n%(errors)s"),
            dict(errors=';\n'.join("%s: %s" % (k, '; '.join(v))
                                   for k, v in exceptions.items()),
                 exc_class=exc_class_name, serialized=serializable_kwargs)
        )
        # We might be able to actually put the following keys' values into
        # format string, but there is no guarantee, drop it just in case.
        for k in exceptions:
            del kwargs[k]
    return serializable_kwargs


class XCAT3Exception(Exception):
    """Base xCAT3 Exception

    To correctly use this class, inherit from it and define
    a '_msg_fmt' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    If you need to access the message from an exception you should use
    six.text_type(exc)

    """
    _msg_fmt = _("An unknown exception occurred.")
    code = http_client.INTERNAL_SERVER_ERROR
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):

        self.kwargs = _ensure_exception_kwargs_serializable(
            self.__class__.__name__, kwargs)

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self._msg_fmt % kwargs

            except Exception as e:
                # kwargs doesn't match a variable in self._msg_fmt
                # log the issue and the kwargs
                prs = ', '.join('%s: %s' % pair for pair in kwargs.items())
                LOG.exception(_LE('Exception in string format operation '
                                  '(arguments %s)'), prs)
                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core self._msg_fmt out if something
                    # happened
                    message = self._msg_fmt

        super(XCAT3Exception, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well."""
        if not six.PY3:
            return six.text_type(self.args[0]).encode('utf-8')

        return self.args[0]

    def __unicode__(self):
        """Return a unicode representation of the exception message."""
        return six.text_type(self.args[0])


class NotAuthorized(XCAT3Exception):
    _msg_fmt = _("Not authorized.")
    code = http_client.FORBIDDEN


class ServiceAlreadyRegistered(XCAT3Exception):
    _msg_fmt = _("Service %(service)s already registered.")


class Invalid(XCAT3Exception):
    _msg_fmt = _("Unacceptable parameters.")
    code = http_client.BAD_REQUEST


class InvalidUUID(Invalid):
    _msg_fmt = _("Expected a UUID but received %(uuid)s.")


class InvalidName(Invalid):
    _msg_fmt = _("Expected a logical name but received %(name)s.")


class InvalidParameterValue(Invalid):
    _msg_fmt = "%(err)s"


class MissingParameterValue(InvalidParameterValue):
    _msg_fmt = "%(err)s"


class NotAcceptable(XCAT3Exception):
    _msg_fmt = _("Request not acceptable")
    code = http_client.NOT_ACCEPTABLE


class NotFound(XCAT3Exception):
    _msg_fmt = _("Resource could not be found")
    code = http_client.NOT_FOUND


class NodeNotFound(NotFound):
    _msg_fmt = _("Node %(node)s could not be found")


class NetworkNotFound(NotFound):
    _msg_fmt = _("Network %(net)s could not be found")


class OSImageNotFound(NotFound):
    _msg_fmt = _("OSImage %(image)s could not be found")


class NoValidHost(NotFound):
    _msg_fmt = _("No valid host was found. Reason: %(reason)s")


class ServiceNotFound(NotFound):
    _msg_fmt = _("Service %(service)s could not be found.")


class ServiceNotExist(NotFound):
    _msg_fmt = _("Could not find any conductor nodes")


class NodeNotAvailable(NotFound):
    _msg_fmt = _("Node %(node)s is not available.")


class Conflict(XCAT3Exception):
    _msg_fmt = _('Conflict.')
    code = http_client.CONFLICT


class DuplicateName(Conflict):
    _msg_fmt = _("A node with name %(name)s already exists.")


class MACAlreadyExists(Conflict):
    _msg_fmt = _("A nic with MAC address %(mac)s already exists.")


class NicAlreadyExists(Conflict):
    _msg_fmt = _("A nic with UUID %(uuid)s already exists.")


class NetworkAlreadyExists(Conflict):
    _msg_fmt = _("A network with name %(name)s already exists.")


class OSImageAlreadyExists(Conflict):
    _msg_fmt = _("A image with name %(name)s already exists.")


class NotAuthorized(XCAT3Exception):
    _msg_fmt = _("Not authorized.")
    code = http_client.FORBIDDEN


class InvalidIdentity(Invalid):
    _msg_fmt = _("Expected a UUID or int but received %(identity)s.")


class OperationNotPermitted(NotAuthorized):
    _msg_fmt = _("Operation not permitted.")


class Invalid(XCAT3Exception):
    _msg_fmt = _("Unacceptable parameters.")
    code = http_client.BAD_REQUEST


class Conflict(XCAT3Exception):
    _msg_fmt = _('Conflict.')
    code = http_client.CONFLICT


class TemporaryFailure(XCAT3Exception):
    _msg_fmt = _("Resource temporarily unavailable, please retry.")
    code = http_client.SERVICE_UNAVAILABLE


class NotAcceptable(XCAT3Exception):
    _msg_fmt = _("Request not acceptable.")
    code = http_client.NOT_ACCEPTABLE


class NotFound(XCAT3Exception):
    _msg_fmt = _("Resource could not be found.")
    code = http_client.NOT_FOUND


class TemporaryFailure(XCAT3Exception):
    _msg_fmt = _("Resource temporarily unavailable, please retry.")
    code = http_client.SERVICE_UNAVAILABLE


class NoFreeAPIWorker(TemporaryFailure):
    _msg_fmt = _('Requested action cannot be performed due to lack of free '
                 'api workers.')
    code = http_client.SERVICE_UNAVAILABLE


class NoFreeServiceWorker(TemporaryFailure):
    _msg_fmt = _('Requested action cannot be performed due to lack of free '
                 'service workers.')
    code = http_client.SERVICE_UNAVAILABLE


class NodeLocked(Conflict):
    _msg_fmt = _("Node %(nodes)s is locked, please retry after the current "
                 "operation is completed.")


class NodeNotLocked(Invalid):
    _msg_fmt = _("Node %(node)s found not to be locked on release")


class NicNotFound(NotFound):
    _msg_fmt = _("Nic %(nic)s could not be found.")


class FileNotFound(NotFound):
    _msg_fmt = _("File %(file)s counld not be found.")


class InvalidNicAttr(Invalid):
    _msg_fmt = _("No node is associated with Nic %(mac)s.")


class PluginNotFound(NotFound):
    _msg_fmt = _("plugin for %(name)s could not been loaded.")


class InvalidFile(Invalid):
    _msg_fmt = _("Can not access file %(name)s.")


class DHCPProcessError(XCAT3Exception):
    _msg_fmt = "%(err)s"


class SSHConnectFailed(XCAT3Exception):
    _msg_fmt = _("Failed to establish SSH connection to host %(host)s.")


class SSHCommandFailed(XCAT3Exception):
    _msg_fmt = _("Failed to execute command via SSH: %(cmd)s.")


class InvalidState(Conflict):
    _msg_fmt = _("Invalid resource state.")


class PowerStateFailure(InvalidState):
    _msg_fmt = _("Failed to set node power state to %(pstate)s.")


class DeployStateFailure(InvalidState):
    _msg_fmt = _("Failed to deploy node %(name)s.")


class ThreadConflict(Conflict):
    _msg_fmt = _(
        "There is anonther thread is running for this job, exit %(thread)s.")
