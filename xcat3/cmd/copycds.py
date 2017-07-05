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
        copycds.create(iso=CONF.command.iso, image=CONF.command.image)


def add_command_parsers(subparsers):
    command_object = CopycdsCommand()

    parser = subparsers.add_parser(
        'create',
        help=_("Create netboot images from Operation System ISO."))
    parser.set_defaults(func=command_object.create)
    parser.add_argument('-n', '--image', nargs='?',
                        help=_("The image name store in xCAT3 system"))
    parser.add_argument('iso', help="The iso file path for operation system")


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help=_('Available commands'),
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    # Only allow create subcommand for copycds command. `create` is also
    # optional argument as it is the default one.
    # `osimage` interface will handle the list, update and delete operation
    # on the image.
    valid_commands = set(['create', ])
    if not set(sys.argv) & valid_commands:
        sys.argv.insert(1, 'create')

    service.prepare_service(sys.argv)
    CONF.command.func()
