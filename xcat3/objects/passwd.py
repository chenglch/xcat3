# coding=utf-8
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
class Passwd(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1'

    dbapi = db_api.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'key': object_fields.StringField(nullable=False),
        'username': object_fields.StringField(nullable=True),
        'password': object_fields.StringField(nullable=False),
        'crypt_method': object_fields.StringField(nullable=True),
    }

    @classmethod
    def get_by_id(cls, context, passwd_id):
        """Find a passwd based on its integer id and return a Passwd object.

        :param passwd_id: the id of a passwd.
        :returns: a :class:`Passwd` object.
        """
        db_passwd = cls.dbapi.get_passwd_by_id(passwd_id)
        passwd = cls._from_db_object(cls(context), db_passwd)
        return passwd

    @classmethod
    def get_by_key(cls, context, key):
        """Find a passwd based on key and return a Passwd object.

        :param key: the key name of a passwd.
        :returns: a :class:`Passwd` object.
        """
        db_passwd = cls.dbapi.get_passwd_by_key(key)
        passwd = cls._from_db_object(cls(context), db_passwd)
        return passwd

    @classmethod
    def list(cls, context):
        """Return a list of Passwd objects.

        :param context: Security context.
        :returns: a list of :class:`Passwd` object.

        """
        db_passwds = cls.dbapi.get_passwd_list()
        passwds = cls._from_db_object_list(context, db_passwds)
        return passwds

    def create(self, context=None):
        """Create a passwd record in the DB.

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
        db_passwd = self.dbapi.create_passwd(values)
        self._from_db_object(self, db_passwd)

    def destroy(self, context=None):
        """Delete the passwd from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        self.dbapi.destroy_passwd(self.key)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this passwd object.

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
        db_passwd = self.dbapi.update_passwd(self.id, updates)
        self.updated_at = db_passwd['updated_at']
        self.obj_reset_changes()
