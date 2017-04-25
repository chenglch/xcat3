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


class Service(base.APIBase):
    """API representation of service.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a service.
    """
    hostname = wsme.wsattr(wtypes.text)
    type = wsme.wsattr(wtypes.text)
    online = types.boolean

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Service.fields)
        for k in fields:
            # Add fields we expose.
            if hasattr(self, k):
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def convert_with_links(s, fields=None):
        service = Service(**s.as_dict())
        service.filter_fields(fields)
        return service


class ServiceCollection(collection.Collection):
    """API representation of a collection of nodes."""

    services = [Service]
    """A list containing service objects"""

    def __init__(self, *args, **kwargs):
        self._type = 'services'

    @staticmethod
    def convert_with_links(services, limit=50, url=None, fields=None,
                           **kwargs):
        collection = ServiceCollection()
        collection.services = [Service.convert_with_links(n, fields=fields)
                               for n in services]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ServiceController(rest.RestController):
    invalid_sort_key_list = ['name']

    _custom_actions = {
        'hostname': ['GET'],
    }

    def _get_services_collection(self, limit=1000, sort_key='id',
                                 sort_dir='asc', fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})
        filters = {}
        services = objects.Service.list(pecan.request.context, limit,
                                        sort_key=sort_key, sort_dir=sort_dir,
                                        filters=filters, fields=None)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        return ServiceCollection.convert_with_links(services, limit,
                                                    fields=fields,
                                                    **parameters)

    @expose.expose(ServiceCollection, types.name, types.listtype)
    def hostname(self, name, fields=None):
        context = pecan.request.context
        service_objs = objects.Service.get_by_hostname(context, name)
        services = [Service.convert_with_links(n, fields=fields)
                    for n in service_objs]
        return ServiceCollection.convert_with_links(services)

    @expose.expose(ServiceCollection, int, wtypes.text, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of services.

        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the xcat3 configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        return self._get_services_collection(limit, sort_key, sort_dir,
                                             fields=fields)
