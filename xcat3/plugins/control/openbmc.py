from oslo_log import log
from xcat3.plugins.control import base
from xcat3.common import exception
from xcat3.common import states
from xcat3.common import rest

import pdb

LOG = log.getLogger(__name__)

url_dict  = {"set_power_state" : "/xyz/openbmc_project/state/host0/attr/RequestedHostTransition",
             "get_power_state"  : "/xyz/openbmc_project/state/host0" }

data_dict = {states.POWER_COMMAND_ON   : "xyz.openbmc_project.State.Host.Transition.On",
             states.POWER_COMMAND_OFF  : "xyz.openbmc_project.State.Host.Transition.Off",
             states.POWER_COMMAND_RESET: "xyz.openbmc_project.State.Host.Transition.Reboot"}

class OPENBMCPlugin(base.ControlInterface) :

    headers = {'Content-Type': 'application/json'}

    def validate(self, node) :
        bmc = node.control_info.get('bmc_address')
        bmcusername = node.control_info.get('bmc_username')
        bmcpassword = node.control_info.get('bmc_password')
        if not bmc :
            raise exception.MissingParameterValue(
                _("OPENBMC address was not specified."))
        if not bmcusername :
            raise exception.MissingParameterValue(
                _("OPENBMC username was not specified."))
        if not bmcpassword :
            raise exception.MissingParameterValue(
                _("OPENBMC password was not specified."))

    def _login(self, node) :
        login_url = 'https://' + node.control_info['bmc_address'] + '/login'
        login_data = { "data": [ node.control_info['bmc_username'], node.control_info['bmc_password'] ] }
        client = rest.RestSession()
        client.request('POST', login_url, OPENBMCPlugin.headers, login_data)

        return client

    def _get_power_state(self, client, node) :
        request_url = 'https://' + node.control_info['bmc_address'] + url_dict['get_power_state']
        rpower_data = client.request('GET', request_url, OPENBMCPlugin.headers, '')
        rpower_state = rpower_data['data']['CurrentHostState']

        return rpower_state

    def get_power_state(self, node) :
        LOG.info("RPC get_power_state called for nodes %(node)s. ",
                 {'node': node.name})

        client = self._login(node)
        rpower_state = self._get_power_state(client, node)

        return rpower_state

    def set_power_state(self, node, power_state) :
        pdb.set_trace

        LOG.info("RPC set_power_state called for nodes %(node)s. "
                 "The desired new state is %(target)s.",
                 {'node': node.name, 'target': power_state})

        client = self._login(node)

        if power_state == states.POWER_COMMAND_BOOT :
            rpower_status = self._get_power_state(client, node)
            if rpower_status == 'xyz.openbmc_project.State.Host.HostState.Off' :
                request_data = { "data": data_dict[states.POWER_COMMAND_ON] }
            else :
                request_data = { "data": data_dict[states.POWER_COMMAND_RESET] }
        elif power_state == states.POWER_COMMAND_ON :
            request_data = { "data": data_dict[states.POWER_COMMAND_ON] }
        elif power_state == states.POWER_COMMAND_OFF :
            request_data = { "data": data_dict[states.POWER_COMMAND_OFF] }
        elif power_state == states.POWER_COMMAND_RESET :
            request_data = { "data": data_dict[states.POWER_COMMAND_RESET] }

        request_url = 'https://' + node.control_info['bmc_address'] + url_dict['set_power_state']
        request_rsp = client.request('PUT', request_url, OPENBMCPlugin.headers, request_data)

    def reboot(self, node) :
        pass


