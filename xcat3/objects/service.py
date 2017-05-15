# coding=utf-8
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#  Updated 2017 for xcat test purpose
#
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

from oslo_versionedobjects import base as object_base
from oslo_log import log
from oslo_utils import timeutils

from xcat3.conf import CONF
from xcat3.common import exception
from xcat3.common.i18n import _, _LC, _LE, _LI, _LW
from xcat3.db import api as db_api
from xcat3.objects import base
from xcat3.objects import fields as object_fields

LOG = log.getLogger(__name__)


@base.XCAT3ObjectRegistry.register
class Service(base.XCAT3Object, object_base.VersionedObjectDictCompat):
    VERSION = '1.0'
    dbapi = db_api.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'hostname': object_fields.StringField(),
        'type': object_fields.StringField(),
        'workers': object_fields.IntegerField(),
        'online': object_fields.BooleanField(),
    }

    @classmethod
    def get_by_hostname(cls, context, hostname):
        """Get a Conductor record by its hostname.

        :param hostname: the hostname on which a Conductor is running
        :returns: a :class:`Conductor` object.
        """
        db_services = cls.dbapi.get_service(hostname)
        services = cls._from_db_object_list(cls(context), db_services)
        return services

    def save(self, context):
        """Save is not supported by Conductor objects."""
        raise NotImplementedError(
            _('Cannot update a service record directly.'))

    def touch(self, context=None):
        """Touch this conductor's DB record, marking it as up-to-date."""
        self.dbapi.touch_service(self.hostname, self.type)

    @classmethod
    def register(cls, context, hostname, type='conductor',
                 update_existing=False):
        """Register an active conductor with the cluster.

        :param hostname: the hostname on which the conductor will run
        :param drivers: the list of drivers enabled in the conductor
        :param update_existing: When false, registration will raise an
                                exception when a conflicting online record
                                is found. When true, will overwrite the
                                existing record. Default: False.
        :raises: ServiceAlreadyRegistered
        :returns: a :class:`Conductor` object.

        """
        try:
            db_cond = cls.dbapi.register_service(
                {'hostname': hostname, 'type': type,
                 'workers': CONF.conductor.workers if
                 type == 'conductor' else 1},
                update_existing=update_existing)
        except Exception as e:
            if 'Duplicate entry' in e.message:
                raise exception.ServiceAlreadyRegistered(
                    service='%s_%s' % (hostname, type))
            else:
                raise e
        return cls._from_db_object(cls(context), db_cond)

    def unregister(self, context=None):
        """Remove this conductor from the service registry."""
        self.dbapi.unregister_service(self.hostname, type=self.type)

    @classmethod
    def list(cls, context, limit=None, sort_key=None, sort_dir=None,
             filters=None, fields=None):
        """Return a list of Service objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`OSImage` object.

        """
        db_services = cls.dbapi.get_services(type=None, check_limit=False)
        services = cls._from_db_object_list(context, db_services)
        interval = CONF.heartbeat_timeout
        limit = timeutils.utcnow() - datetime.timedelta(seconds=interval)
        for service in services:
            # offset-naive and offset-aware datetimes, remove timezone aware
            if service.updated_at.replace(tzinfo=None) < limit:
                service.online = False
        return services
