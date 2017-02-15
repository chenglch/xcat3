# -*- encoding: utf-8 -*-

"""The xCAT3 Service API."""

import sys

from oslo_config import cfg

from xcat3.common import service as xcat3_service
from xcat3.common import wsgi_service

CONF = cfg.CONF


def main():
    # Parse config file and command line options, then start logging
    xcat3_service.prepare_service(sys.argv)

    # Build and start the WSGI app
    launcher = xcat3_service.process_launcher()
    server = wsgi_service.WSGIService('xcat3_api', CONF.api.enable_ssl_api)
    launcher.launch_service(server, workers=server.workers)
    launcher.wait()

if __name__ == '__main__':
    sys.exit(main())