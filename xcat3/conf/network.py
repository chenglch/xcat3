# Updated 2017 for xcat test purpose
# Copyright 2016 Intel Corporation
# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 International Business Machines Corporation
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

from xcat3.common.i18n import _

opts = [
    cfg.IntOpt('workers_pool_size',
               default=10, min=10,
               help=_('The size of the workers greenthread pool. ')),
    cfg.IntOpt('timeout',
               default=3660,
               help=_('Maximum time (in seconds) to process task in a worker'
                      'thread.')),
]


def register_opts(conf):
    conf.register_opts(opts, group='network')
