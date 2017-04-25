# Copyright (c) 2012 NTT DOCOMO, INC.
# Copyright 2010 OpenStack Foundation
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

"""
Mapping of bare metal node states.

Setting the node `power_state` is handled by the conductor's power
synchronization thread. Based on the power state retrieved from the driver
for the node, the state is set to POWER_ON or POWER_OFF, accordingly.
Should this fail, the `power_state` value is left unchanged, and the node
is placed into maintenance mode.

The `power_state` can also be set manually via the API. A failure to change
the state leaves the current state unchanged. The node is NOT placed into
maintenance mode in this case.
"""

from oslo_log import log as logging

LOG = logging.getLogger(__name__)

##############
# Power states
##############

POWER_ON = 'on'
""" Node is powered on. """

POWER_OFF = 'off'
""" Node is powered off. """

################
# Request states
################

FAIL = 'failed'
SUCCESS = 'ok'
DELETED = 'deleted'
UPDATED = 'updated'

################
# Power command
################

POWER_COMMAND_ON = 'on'
POWER_COMMAND_OFF = 'off'
POWER_COMMAND_BOOT = 'boot'
POWER_COMMAND_RESET = 'reset'


ERROR = 'error'

##################
# Provision states
##################

DEPLOY_NONE = None
DEPLOY_DHCP = 'dhcp'
DEPLOY_NODESET = 'nodeset'
