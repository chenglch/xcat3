# Copyright 2013 Red Hat, Inc.
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

import inspect

import jsonpatch
from oslo_config import cfg
from oslo_utils import uuidutils
import pecan
import wsme

from xcat3.api.controllers.v1 import versions
from xcat3.common import exception
from xcat3.common.i18n import _
from xcat3.common import utils
from xcat3 import objects


CONF = cfg.CONF


JSONPATCH_EXCEPTIONS = (jsonpatch.JsonPatchException,
                        jsonpatch.JsonPointerException,
                        KeyError)


def validate_limit(limit):
    if limit is None:
        return CONF.api.max_limit

    if limit <= 0:
        raise wsme.exc.ClientSideError(_("Limit must be positive"))

    return min(CONF.api.max_limit, limit)


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise wsme.exc.ClientSideError(_("Invalid sort direction: %s. "
                                         "Acceptable values are "
                                         "'asc' or 'desc'") % sort_dir)
    return sort_dir


def apply_jsonpatch(doc, patch):
    for p in patch:
        if p['op'] == 'add' and p['path'].count('/') == 1:
            if p['path'].lstrip('/') not in doc:
                msg = _('Adding a new attribute (%s) to the root of '
                        ' the resource is not allowed')
                raise wsme.exc.ClientSideError(msg % p['path'])
    return jsonpatch.apply_patch(doc, jsonpatch.JsonPatch(patch))


def get_patch_values(patch, path):
    """Get the patch values corresponding to the specified path.

    If there are multiple values specified for the same path
    (for example the patch is [{'op': 'add', 'path': '/name', 'value': 'abc'},
                               {'op': 'add', 'path': '/name', 'value': 'bca'}])
    return all of them in a list (preserving order).

    :param patch: HTTP PATCH request body.
    :param path: the path to get the patch values for.
    :returns: list of values for the specified path in the patch.
    """
    return [p['value'] for p in patch
            if p['path'] == path and p['op'] != 'remove']


def is_path_removed(patch, path):
    """Returns whether the patch includes removal of the path (or subpath of).

    :param patch: HTTP PATCH request body.
    :param path: the path to check.
    :returns: True if path or subpath being removed, False otherwise.
    """
    path = path.rstrip('/')
    for p in patch:
        if ((p['path'] == path or p['path'].startswith(path + '/')) and
                p['op'] == 'remove'):
            return True


def is_path_updated(patch, path):
    """Returns whether the patch includes operation on path (or its subpath).

    :param patch: HTTP PATCH request body.
    :param path: the path to check.
    :returns: True if path or subpath being patched, False otherwise.
    """
    path = path.rstrip('/')
    for p in patch:
        return p['path'] == path or p['path'].startswith(path + '/')


def get_node_obj(node):
    """Get the RPC node from the node name.

    :param node: the api node.

    :returns: The RPC Node.
    :raises: InvalidName if the name provided is not valid.
    :raises: NodeNotFound if the node is not found.
    """
    context = pecan.request.context
    if type(node.name) != wsme.types.UnsetType:
        node_obj = objects.Node.get_by_name(context, node.name)
        if not node_obj:
            raise exception.NodeNotFound(node=node.name)
        return node_obj

    raise exception.InvalidName(name=node)


def get_node_name(node):
    """Get the node name from api node.

    :param node: the api node.

    :return: the name of api node
    :raises: InvalidName if the name provided is not valid.
    """
    context = pecan.request.context
    if type(node.name) != wsme.types.UnsetType:
        return node.name

    raise exception.InvalidName(name=node)


def is_valid_node_name(name):
    """Determine if the provided name is a valid node name.

    Check to see that the provided node name is valid.

    :param: name: the node name to check.
    :returns: True if the name is valid, False otherwise.
    """
    return utils.is_valid_logical_name(name)
