# Copyright (c) 2015 Intel Corporation
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

# This is the version 1 API
BASE_VERSION = 1

MINOR_0_JUNO = 0
MINOR_1_INITIAL_VERSION = 1
MINOR_2_AVAILABLE_STATE = 2
MINOR_3_DRIVER_INTERNAL_INFO = 3
MINOR_4_MANAGEABLE_STATE = 4
MINOR_5_NODE_NAME = 5
MINOR_6_INSPECT_STATE = 6
MINOR_7_NODE_CLEAN = 7
MINOR_8_FETCHING_SUBSET_OF_FIELDS = 8
MINOR_9_PROVISION_STATE_FILTER = 9
MINOR_10_UNRESTRICTED_NODE_NAME = 10
MINOR_11_ENROLL_STATE = 11
MINOR_12_RAID_CONFIG = 12
MINOR_13_ABORT_VERB = 13
MINOR_14_LINKS_NODESTATES_DRIVERPROPERTIES = 14
MINOR_15_MANUAL_CLEAN = 15
MINOR_16_DRIVER_FILTER = 16
MINOR_17_ADOPT_VERB = 17
MINOR_18_PORT_INTERNAL_INFO = 18
MINOR_19_PORT_ADVANCED_NET_FIELDS = 19
MINOR_20_NETWORK_INTERFACE = 20
MINOR_21_RESOURCE_CLASS = 21
MINOR_22_LOOKUP_HEARTBEAT = 22
MINOR_23_PORTGROUPS = 23
MINOR_24_PORTGROUPS_SUBCONTROLLERS = 24
MINOR_25_UNSET_CHASSIS_UUID = 25
MINOR_26_PORTGROUP_MODE_PROPERTIES = 26
MINOR_27_SOFT_POWER_OFF = 27
MINOR_28_VIFS_SUBCONTROLLER = 28
MINOR_29_INJECT_NMI = 29
MINOR_30_DYNAMIC_DRIVERS = 30
MINOR_31_DYNAMIC_INTERFACES = 31

# When adding another version, update MINOR_MAX_VERSION and also update
# doc/source/dev/webapi-version-history.rst with a detailed explanation of
# what the version has changed.
MINOR_MAX_VERSION = MINOR_31_DYNAMIC_INTERFACES

# String representations of the minor and maximum versions
MIN_VERSION_STRING = '{}.{}'.format(BASE_VERSION, MINOR_1_INITIAL_VERSION)
MAX_VERSION_STRING = '{}.{}'.format(BASE_VERSION, MINOR_MAX_VERSION)
