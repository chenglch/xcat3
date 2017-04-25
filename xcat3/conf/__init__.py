# Copyright 2016 OpenStack Foundation
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

from oslo_config import cfg

from xcat3.conf import api
from xcat3.conf import conductor
from xcat3.conf import database
from xcat3.conf import default
from xcat3.conf import deploy
from xcat3.conf import network


CONF = cfg.CONF

api.register_opts(CONF)
conductor.register_opts(CONF)
database.register_opts(CONF)
default.register_opts(CONF)
deploy.register_opts(CONF)
network.register_opts(CONF)