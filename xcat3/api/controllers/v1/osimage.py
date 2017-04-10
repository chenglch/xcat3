# Copyright 2013 Hewlett-Packard Development Company, L.P.
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


class OSImage(base.APIBase):
    """API representation of image.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a image.
    """
    name = wsme.wsattr(wtypes.text)
    """The name of image"""
    ver = wsme.wsattr(wtypes.text)
    arch = wsme.wsattr(wtypes.text)
    distro = wsme.wsattr(wtypes.text)
    profile = wsme.wsattr(wtypes.text)
    provmethod = wsme.wsattr(wtypes.text)
    rootfstype = wsme.wsattr(wtypes.text)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.OSImage.fields)
        for k in fields:
            # Add fields we expose.
            if hasattr(self, k):
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @classmethod
    def get_api_image(cls, name):
        return cls(name=name)

    @staticmethod
    def convert_with_links(net, fields=None):
        image = OSImage(**net.as_dict())
        return image


class OSImagePatchType(types.JsonPatchType):
    _api_base = OSImage

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults


class OSImageCollection(collection.Collection):
    """API representation of a collection of nodes."""

    images = [OSImage]
    """A list containing image objects"""

    def __init__(self, *args, **kwargs):
        self._type = 'images'

    @staticmethod
    def convert_with_links(images, limit=50, url=None, fields=None,
                           **kwargs):
        collection = OSImageCollection()
        collection.images = [OSImage.convert_with_links(n, fields=fields)
                             for n in images]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class OSImageController(rest.RestController):
    invalid_sort_key_list = ['name']

    def _get_images_collection(self, limit=1000, sort_key='id',
                               sort_dir='asc', fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})
        filters = {}
        images = objects.OSImage.list(pecan.request.context, limit,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters, fields=None)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        return OSImageCollection.convert_with_links(images, limit,
                                                    fields=fields,
                                                    **parameters)

    def _update_changed_fields(self, image, image_obj):
        """Update rpc_image based on changed fields in a image.

        """
        for field in objects.OSImage.fields:
            try:
                patch_val = getattr(image, field)
            except AttributeError:
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if image_obj[field] != patch_val:
                image_obj[field] = patch_val

    @expose.expose(OSImage, types.name, types.listtype)
    def get_one(self, name, fields=None):
        context = pecan.request.context
        image_obj = objects.OSImage.get_by_name(context, name)
        return OSImage.convert_with_links(image_obj, fields=fields)

    @expose.expose(OSImageCollection, int, wtypes.text, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of images.

        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the xcat3 configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        if fields is None:
            fields = ['name']
        return self._get_images_collection(limit, sort_key, sort_dir,
                                           fields=fields)

    @expose.expose(types.jsontype, body=OSImage,
                   status_code=http_client.CREATED)
    def post(self, image):
        """Create image

        :param image: image with the request
        """
        context = pecan.request.context
        if not hasattr(image, 'name'):
            raise exception.InvalidParameterValue(
                _("Invalid request parameter %(image)s") % {
                    'image': str(image)})
        new_image = objects.OSImage(context, **image.as_dict())
        new_image.create()
        result = {'image': dict()}
        result['image'][image.name] = 'ok'
        return types.JsonType.validate(result)

    @expose.expose(None, types.name, status_code=http_client.ACCEPTED)
    def delete(self, name):
        """Delete image

        :param nodes: image name to delete, api format
        """
        context = pecan.request.context
        image_obj = objects.OSImage.get_by_name(context, name)
        image_obj.destroy(name)

    @expose.expose(OSImage, types.name, body=[OSImagePatchType])
    def patch(self, name, patch):
        """Update an existing image.

        :param name: The name of image.
        :param patch: a json PATCH document to apply to this image.
        :return: json format api node
        """
        context = pecan.request.context
        image_obj = objects.OSImage.get_by_name(context, name)
        names = api_utils.get_patch_values(patch, '/name')
        if len(names):
            error_msg = (_("OSImage %s: Cannot change name to invalid name ")
                         % name)
            error_msg += "'%(name)s'"
        try:
            image_dict = image_obj.as_dict()
            image = OSImage(**api_utils.apply_jsonpatch(image_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        self._update_changed_fields(image, image_obj)
        image_obj.save()
        api_image = OSImage.convert_with_links(image_obj)
        return api_image
