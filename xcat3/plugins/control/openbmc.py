from oslo_log import log

from xcat3.common import client as http_client
from xcat3.common import exception
from xcat3.common import states

from xcat3.plugins.control import base

LOG = log.getLogger(__name__)

url_dict = {
    "set_power_state":
        "/xyz/openbmc_project/state/host0/attr/RequestedHostTransition",
    "get_power_state":
        "/xyz/openbmc_project/state/host0"}

data_dict = {
    states.POWER_COMMAND_ON:
        "xyz.openbmc_project.State.Host.Transition.On",
    states.POWER_COMMAND_OFF:
        "xyz.openbmc_project.State.Host.Transition.Off",
    states.POWER_COMMAND_RESET:
        "xyz.openbmc_project.State.Host.Transition.Reboot"}


class OPENBMCPlugin(base.ControlInterface):
    headers = {'Content-Type': 'application/json'}

    def validate(self, node):
        bmc_address = node.control_info.get('bmc_address')
        bmcusername = node.control_info.get('bmc_username')
        bmcpassword = node.control_info.get('bmc_password')
        if not bmc_address:
            raise exception.MissingParameterValue(
                _("OPENBMC address was not specified."))
        if not bmcusername:
            raise exception.MissingParameterValue(
                _("OPENBMC username was not specified."))
        if not bmcpassword:
            raise exception.MissingParameterValue(
                _("OPENBMC password was not specified."))

    def _login(self, node):
        login_url = 'https://' + node.control_info['bmc_address'] + '/login'
        login_data = {"data": [node.control_info['bmc_username'],
                               node.control_info['bmc_password']]}
        client = http_client.HttpClient()
        client.post(login_url, headers=self.headers, data=login_data)
        return client

    def _get_power_state(self, client, node):
        request_url = 'https://' + node.control_info['bmc_address'] + url_dict[
            'get_power_state']
        reap, body = client.get(request_url, headers=self.headers)
        return body['data']['CurrentHostState']

    def get_power_state(self, node):
        client = self._login(node)
        return self._get_power_state(client, node)

    def set_power_state(self, node, power_state):
        client = self._login(node)

        if power_state == states.POWER_COMMAND_BOOT:
            rpower_status = self._get_power_state(client, node)
            if rpower_status == 'xyz.openbmc_project.State.Host.HostState.Off':
                request_data = {"data": data_dict[states.POWER_COMMAND_ON]}
            else:
                request_data = {"data": data_dict[states.POWER_COMMAND_RESET]}
        elif power_state == states.POWER_COMMAND_ON:
            request_data = {"data": data_dict[states.POWER_COMMAND_ON]}
        elif power_state == states.POWER_COMMAND_OFF:
            request_data = {"data": data_dict[states.POWER_COMMAND_OFF]}
        elif power_state == states.POWER_COMMAND_RESET:
            request_data = {"data": data_dict[states.POWER_COMMAND_RESET]}

        request_url = 'https://' + node.control_info['bmc_address'] + url_dict[
            'set_power_state']
        client.put(request_url, self.headers, request_data)

    def reboot(self, node):
        pass
