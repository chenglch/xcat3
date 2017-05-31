# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Updated 2017 for xcat test purpose
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

import datetime

import pecan
from oslo_log import log
from pecan import rest
from xcat3.api import expose
import xcat3.conf
from six.moves import http_client
from xcat3.common import exception
from xcat3.api.controllers.v1 import types
import wsme
from wsme import types as wtypes

from xcat3.api.controllers import base
from xcat3.api.controllers.v1 import collection
from xcat3.api.controllers.v1 import utils as api_utils
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3 import objects

CONF = xcat3.conf.CONF

LOG = log.getLogger(__name__)


class Passwd(base.APIBase):
    """API representation of image.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a image.
    """
    key = wsme.wsattr(wtypes.text, mandatory=True)
    """The key name of passwd"""
    username = wsme.wsattr(wtypes.text)
    password = wsme.wsattr(wtypes.text)
    crypt_method = wsme.wsattr(wtypes.text)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Passwd.fields)
        for k in fields:
            # Add fields we expose.
            if hasattr(self, k):
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @classmethod
    def get_api_passwd(cls, key):
        return cls(key=key)

    @staticmethod
    def convert_with_links(net, fields=None):
        passwd = Passwd(**net.as_dict())
        return passwd


class PasswdPatchType(types.JsonPatchType):
    _api_base = Passwd

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        defaults.append('key')
        return defaults


class PasswdCollection(collection.Collection):
    """API representation of a collection of passwds."""

    passwds = [Passwd]
    """A list containing image objects"""

    def __init__(self, *args, **kwargs):
        self._type = 'passwds'

    @staticmethod
    def convert_with_links(passwds, url=None, fields=None,**kwargs):
        collection = PasswdCollection()
        collection.passwds = [Passwd.convert_with_links(n, fields=fields)
                             for n in passwds]
        collection.next = collection.get_next(None, url=url, **kwargs)
        return collection


class PasswdController(rest.RestController):
    invalid_sort_key_list = ['key']

    _custom_actions = {
        'get_by_id': ['GET']
    }

    def _update_changed_fields(self, passwd, passwd_obj):
        """Update rpc_passwd based on changed fields in a passwd.

        """
        for field in objects.Passwd.fields:
            try:
                patch_val = getattr(passwd, field)
            except AttributeError:
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if passwd_obj[field] != patch_val:
                passwd_obj[field] = patch_val

    @expose.expose(Passwd, int, types.listtype)
    def get_by_id(self, id, fields=None):
        context = pecan.request.context
        passwd_obj = objects.Passwd.get_by_id(context, id)
        return Passwd.convert_with_links(passwd_obj, fields=fields)

    @expose.expose(Passwd, types.name, types.listtype)
    def get_one(self, key, fields=None):
        context = pecan.request.context
        passwd_obj = objects.Passwd.get_by_key(context, key)
        return Passwd.convert_with_links(passwd_obj, fields=fields)

    @expose.expose(PasswdCollection, int, wtypes.text, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of passwds.

        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the xcat3 configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        passwds = objects.Passwd.list(pecan.request.context)
        return PasswdCollection.convert_with_links(passwds)

    @expose.expose(types.jsontype, body=Passwd,
                   status_code=http_client.CREATED)
    def post(self, passwd):
        """Create passwd

        :param passwd: passwd with the request
        """
        context = pecan.request.context
        new_passwd = objects.Passwd(context, **passwd.as_dict())
        new_passwd.create()
        result = {'passwd': dict()}
        result['passwd'][passwd.key] = 'ok'
        return types.JsonType.validate(result)

    @expose.expose(None, types.name, status_code=http_client.ACCEPTED)
    def delete(self, key):
        """Delete passwd

        :param nodes: passwd key to delete, api format
        """
        context = pecan.request.context
        passwd_obj = objects.Passwd.get_by_key(context, key)
        passwd_obj.destroy()

    @expose.expose(Passwd, types.name, body=[PasswdPatchType])
    def patch(self, key, patch):
        """Update an existing passwd.

        :param key: The key of passwd.
        :param patch: a json PATCH document to apply to this passwd.
        :return: json format api node
        """
        context = pecan.request.context
        passwd_obj = objects.Passwd.get_by_key(context, key)
        try:
            passwd_dict = passwd_obj.as_dict()
            passwd = Passwd(**api_utils.apply_jsonpatch(passwd_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        self._update_changed_fields(passwd, passwd_obj)
        passwd_obj.save()
        api_passwd = Passwd.convert_with_links(passwd_obj)
        return api_passwd
