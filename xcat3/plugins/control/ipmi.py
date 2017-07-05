# coding=utf-8

# Copyright 2013 International Business Machines Corporation
# Updated 2017 for xcat test purpose
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

from oslo_log import log
from pyghmi import exceptions as pyghmi_exception
from pyghmi.ipmi import command as ipmi_command
from xcat3.plugins.control import base
from xcat3.common import exception
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3.common import states
from xcat3.common import boot_device

LOG = log.getLogger(__name__)


class IPMIPlugin(base.ControlInterface):
    _BOOT_DEVICES_MAP = {
        boot_device.DISK: 'hd',
        boot_device.NET: 'network',
        boot_device.CDROM: 'cdrom',
    }

    def validate(self, node):
        """check the ipmi specific attributes"""
        if not node.control_info.has_key('bmc_address'):
            raise exception.MissingParameterValue(
                _("IPMI address was not specified."))
        if not node.control_info.has_key('bmc_username'):
            raise exception.MissingParameterValue(
                _("IPMI username was not specified."))

    def get_power_state(self, node):
        """Return the power state of the node

        :param node: the node to act on.
        :raises: IpmiException when the native ipmi call fails.
        :returns: a power state.
        """
        address = node.control_info.get('bmc_address')
        username = node.control_info.get('bmc_username')
        password = node.control_info.get('bmc_password')
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            ret = ipmicmd.get_power()
            ipmicmd.ipmi_session.logout()
        except pyghmi_exception.IpmiException as e:
            msg = (_("IPMI get power state failed for node %(node)s "
                     "with the following error: %(error)s") %
                   {'node': node.name, 'error': e})
            LOG.error(msg)
            raise exception.IPMIFailure(msg)

        state = ret.get('powerstate')
        if state == 'on':
            return states.POWER_ON
        elif state == 'off':
            return states.POWER_OFF
        else:
            # NOTE(linggao): Do not throw an exception here because it might
            # return other valid values. It is up to the caller to decide
            # what to do.
            LOG.warning(
                _LW("IPMI get power state for node %(node)s returns the"
                    " following details: %(detail)s"),
                {'node': node.name, 'detail': ret})
            return states.ERROR

    def _power_on(self, node, address, username, password=None):
        """Turn the power on for this node.

        :param address: the bmc access info for a node.
        :param username: the bmc user name info for a node.
        :param password: the bmc password info for a node.
        :returns: power state POWER_ON, one of :class:`xcat3.common.states`.
        :raises: IPMIFailure when the native ipmi call fails.
        :raises: PowerStateFailure when invalid power state is returned
                 from ipmi.
        """

        msg = _("IPMI power on failed for node %(node)s with the "
                "following error: %(error)s")
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            # NOTE(chenglch): Do not return directly as the BMC for OpenPOWER
            # servers is very fragile, we always get timeout error from BMC.
            ret = ipmicmd.set_power('on', False)
            ipmicmd.ipmi_session.logout()
        except pyghmi_exception.IpmiException as e:
            error = msg % {'node': node.name, 'error': e}
            LOG.error(error)
            raise exception.IPMIFailure(error)

        state = ret.get('powerstate') or ret.get('pendingpowerstate')
        if state == 'on':
            return states.POWER_ON
        else:
            error = _("bad response: %s") % ret
            LOG.error(msg, {'node': node.name, 'error': error})
            raise exception.PowerStateFailure(pstate=states.POWER_ON)

    def _power_off(self, node, address, username, password=None):
        """Turn the power off for this node.

        :param address: the bmc access info for a node.
        :param username: the bmc user name info for a node.
        :param password: the bmc password info for a node.
        :returns: power state POWER_OFF, one of :class:`xcat3.common.states`.
        :raises: IPMIFailure when the native ipmi call fails.
        :raises: PowerStateFailure when invalid power state is returned
                 from ipmi.
        """

        msg = _("IPMI power off failed for node %(node)s with the "
                "following error: %(error)s")
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            #NOTE(chenglch): Do not return directly as the BMC for OpenPOWER
            # servers is very fragile, we always get timeout error from BMC.
            ret = ipmicmd.set_power('off', False)
            ipmicmd.ipmi_session.logout()
        except pyghmi_exception.IpmiException as e:
            error = msg % {'node': node.name, 'error': e}
            LOG.error(error)
            raise exception.IPMIFailure(error)

        state = ret.get('powerstate') or ret.get('pendingpowerstate')
        if state == 'off':
            return states.POWER_OFF
        else:
            error = _("bad response: %s") % ret
            LOG.error(msg, {'node': node.name, 'error': error})
            raise exception.PowerStateFailure(pstate=states.POWER_OFF)

    def _reboot(self, node, address, username, password=None):
        """Reboot this node.

        If the power is off, turn it on. If the power is on, reset it.

        :param address: the bmc access info for a node.
        :param username: the bmc user name info for a node.
        :param password: the bmc password info for a node.
        :returns: power state POWER_ON, one of :class:`xcat3.common.states`.
        :raises: IPMIFailure when the native ipmi call fails.
        :raises: PowerStateFailure when invalid power state is returned
                 from ipmi.
        """

        msg = _("IPMI power reboot failed for node %(node)s with the "
                "following error: %(error)s")
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            # NOTE(chenglch): Do not return directly as the BMC for OpenPOWER
            # servers is very fragile, we always get timeout error from BMC.
            ret = ipmicmd.set_power('boot', False)
            ipmicmd.ipmi_session.logout()
        except pyghmi_exception.IpmiException as e:
            error = msg % {'node': node.name, 'error': e}
            LOG.error(error)
            raise exception.IPMIFailure(error)

        if 'error' in ret:
            error = _("bad response: %s") % ret
            LOG.error(msg, {'node': node.name, 'error': error})
            raise exception.PowerStateFailure(pstate=states.REBOOT)

        return states.POWER_ON

    def set_power_state(self, node, power_state):
        """Set the power state of the node's node.

        :param node: the node to act on.
        :param power_state: Any power state.
        :raises: IPMIFailure when the native ipmi call fails.
        :raises: PowerStateFailure when invalid power state is returned
                 from ipmi.
        :raises: InvalidParameterValue when invalid power state is specified.
        """
        address = node.control_info.get('bmc_address')
        username = node.control_info.get('bmc_username')
        password = node.control_info.get('bmc_password')
        if power_state == states.POWER_ON:
            self._power_on(node, address, username, password)
        elif power_state == states.POWER_OFF:
            self._power_off(node, address, username, password)
        elif power_state == states.REBOOT:
            self._reboot(node, address, username, password)
        else:
            raise exception.InvalidParameterValue(
                _("set_power_state called with an invalid power state: %s."
                  ) % power_state)

    def get_boot_device(self, node):
        """Return the boot device of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :returns: the boot device
        """
        address = node.control_info.get('bmc_address')
        username = node.control_info.get('bmc_username')
        password = node.control_info.get('bmc_password')
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            ret = ipmicmd.get_bootdev()
            ipmicmd.ipmi_session.logout()
            if 'error' in ret:
                raise pyghmi_exception.IpmiException(ret['error'])
        except pyghmi_exception.IpmiException as e:
            LOG.error(_LE("IPMI get boot device failed for node %(node)s "
                          "with the following error: %(error)s"),
                      {'node': node.name, 'error': e})
            raise exception.IPMIFailure(cmd=e)

        response = boot_device.UNKNOWN
        bootdev = ret.get('bootdev')
        if bootdev is not None:
            response = next(
                (dev for dev, hdev in self._BOOT_DEVICES_MAP.items() if
                 hdev == bootdev), boot_device.UNKNOWN)
            if response == boot_device.UNKNOWN:
                LOG.warning(_LW('IPMI get boot device for node %(node)s return'
                                ' %(bootdev)s'),
                            {'node': node.name, 'bootdev': bootdev})
        return response

    def set_boot_device(self, node, boot_device):
        """Set the boot device of the node

        :param node: the node to act on.
        :raises: MissingParameterValue if a required parameter is missing.
        :raises: InvalidParameterValue if boot_device is not supported.
        :raises: IPMIFailure when the native ipmi call fails.
        """
        if boot_device not in self._BOOT_DEVICES_MAP.keys():
            raise exception.InvalidParameterValue(_(
                "Invalid boot device %s specified.") % boot_device)

        address = node.control_info.get('bmc_address')
        username = node.control_info.get('bmc_username')
        password = node.control_info.get('bmc_password')
        try:
            ipmicmd = ipmi_command.Command(bmc=address,
                                           userid=username,
                                           password=password)
            bootdev = self._BOOT_DEVICES_MAP[boot_device]
            ipmicmd.set_bootdev(bootdev)
            ipmicmd.ipmi_session.logout()
        except pyghmi_exception.IpmiException as e:
            LOG.error(_LE("IPMI set boot device failed for node %(node)s "
                          "with the following error: %(error)s"),
                      {'node': node.name, 'error': e})
            raise exception.IPMIFailure(cmd=e)

    def get_inventory(self, node):
        """Get the inventory information from control module

        :param node: the node to act on.
        """
        pass
