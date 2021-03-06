# -*- encoding: utf-8 -*-
#
# Copyright © 2012 eNovance <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Updated for xcat3 purpose

from oslo_log import log
from oslo_service import service

from xcat3.common import config
from xcat3.conf import CONF
from xcat3 import objects

LOG = log.getLogger(__name__)


def prepare_service(argv=None):
    argv = [] if argv is None else argv
    log.register_options(CONF)
    log.set_defaults(default_log_levels=['amqp=WARNING',
                                         'amqplib=WARNING',
                                         'qpid.messaging=INFO',
                                         'oslo_messaging=INFO',
                                         'sqlalchemy=WARNING',
                                         'stevedore=INFO',
                                         'eventlet.wsgi.server=INFO',
                                         'iso8601=WARNING',
                                         'paramiko=WARNING',
                                         'requests=WARNING',
                                         'urllib3.connectionpool=WARNING',
                                         ])
    config.parse_args(argv)
    log.setup(CONF, 'xcat3')
    objects.register_all()


def process_launcher():
    return service.ProcessLauncher(CONF)
