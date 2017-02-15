# -*- encoding: utf-8 -*-

"""
The xCAT Management Service
"""

import sys

from oslo_config import cfg
from oslo_log import log
from oslo_service import service

from xcat3.common.i18n import _LW
from xcat3.common import rpc_service
from xcat3.common import service as xcat3_service

CONF = cfg.CONF

LOG = log.getLogger(__name__)


def main():
    assert 'xcat3.conductor.manager' not in sys.modules

    # Parse config file and command line options, then start logging
    xcat3_service.prepare_service(sys.argv)

    mgr = rpc_service.RPCService(CONF.host,
                                 'xcat3.conductor.manager',
                                 'ConductorManager')

    launcher = service.launch(CONF, mgr)
    launcher.wait()


if __name__ == '__main__':
    sys.exit(main())
