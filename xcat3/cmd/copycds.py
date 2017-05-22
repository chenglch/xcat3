# -*- encoding: utf-8 -*-
"""
Build netboot image from ISO
"""

import sys

from oslo_config import cfg

from xcat3.common.i18n import _
from xcat3.common import service
from xcat3.conf import CONF
from xcat3.copycd import copycds

class CopycdsCommand(object):
    def create(self):
        copycds.create(iso=CONF.command.iso, image=CONF.command.image,
                       install_dir=CONF.command.install)

    def delete(self):
        pass


def add_command_parsers(subparsers):
    command_object = CopycdsCommand()

    parser = subparsers.add_parser(
        'create',
        help=_("Create netboot images from Operation System ISO."))
    parser.set_defaults(func=command_object.create)
    parser.add_argument('-n', '--image', nargs='?',
                        help=_("The image name store in xCAT3 system"))
    parser.add_argument('--install', nargs='?',
                        help=_("Install direcotory of image"))
    parser.add_argument('iso', help="The iso file path for operation system")
    # delete
    parser = subparsers.add_parser('delete',
                                   help=_("Delete netboot image."))

    parser.add_argument('--image')
    parser.set_defaults(func=command_object.delete)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help=_('Available commands'),
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    # this is hack to work with previous usage of xcat3-dbsync
    # pls change it to xcat3-dbsync upgrade
    valid_commands = set(['create', 'delete'])
    if not set(sys.argv) & valid_commands:
        sys.argv.append('create')

    service.prepare_service(sys.argv)
    CONF.command.func()
