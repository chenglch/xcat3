# coding=utf-8
#
#    Updated 2017 for xcat test purpose
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

from oslo_versionedobjects import base as object_base

from xcat3.db import api as db_api
from xcat3.objects import base
from xcat3.objects import fields as object_fields


@base.XCAT3ObjectRegistry.register
class OSImage(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1'

    dbapi = db_api.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'name': object_fields.StringField(nullable=False),
        'ver': object_fields.StringField(nullable=False),
        'arch': object_fields.StringField(nullable=False),
        'distro': object_fields.StringField(nullable=False),
        'profile': object_fields.StringField(nullable=True),
        'type': object_fields.StringField(nullable=True),
        'provmethod': object_fields.StringField(nullable=True),
        'rootfstype': object_fields.StringField(nullable=True),
    }

    @classmethod
    def get_by_id(cls, context, image_id):
        """Find a network based on its integer id and return a OSImage object.

        :param network_id: the id of a image.
        :returns: a :class:`OSImage` object.
        """
        db_image = cls.dbapi.get_image_by_id(image_id)
        image = cls._from_db_object(cls(context), db_image)
        return image

    @classmethod
    def get_by_name(cls, context, name):
        """Find a image based on name and return a OSImage object.

        :param name: the name of a image.
        :returns: a :class:`OSImage` object.
        """
        db_image = cls.dbapi.get_image_by_name(name)
        image = cls._from_db_object(cls(context), db_image)
        return image

    @classmethod
    def list(cls, context, limit=None, sort_key=None, sort_dir=None,
             filters=None, fields=None):
        """Return a list of Node objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`OSImage` object.

        """
        db_images = cls.dbapi.get_image_list(filters=filters, limit=limit,
                                             sort_key=sort_key,
                                             sort_dir=sort_dir)
        images = cls._from_db_object_list(context, db_images)
        return images

    def create(self, context=None):
        """Create a image record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        values = self.obj_get_changes()
        db_image = self.dbapi.create_image(values)
        self._from_db_object(self, db_image)

    def destroy(self, context=None):
        """Delete the image from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        self.dbapi.destroy_image(self.name)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this image.

        Column-wise updates will be made based on the result of
        self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        :raises: InvalidParameterValue if some property values are invalid.
        """
        updates = self.obj_get_changes()
        db_image = self.dbapi.update_image(self.id, updates)
        self.updated_at = db_image['updated_at']
        self.obj_reset_changes()
