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
import functools

from webob import exc
import wsme
from wsme import types as wtypes

from xcat3.db import api as db_api
from xcat3.common.i18n import _

EXCEPTION_MSG = '%s: Please see the detail in the api log file'
dbapi = db_api.get_instance()


class APIBase(wtypes.Base):
    created_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is created"""

    updated_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is updated"""

    def as_dict(self):
        """Render this object as a dict of its fields."""
        return dict((k, getattr(self, k))
                    for k in self.fields
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)

    def filter_fields(self, show_list=None, remove_list=None):
        """Unset fields so they don't appear in the message body.

        :param show_list: A list of fields that won't be touched.
        :param remove_list: A list of fields will be hide.

        """
        if remove_list is None:
            remove_list = []

        for k in self.as_dict():
            if show_list and k not in show_list:
                setattr(self, k, wsme.Unset)
            if k in remove_list:
                setattr(self, k, wsme.Unset)

    @classmethod
    def filter_dict(cls, dct, show_list=None, remove_list=None):
        """Unset fields so they don't appear in the message body.

        :param dct: A dict contains the return fields.
        :param show_list: A list of fields that won't be touched.
        :param remove_list: A list of fields will be hide.
        """
        if remove_list is None:
            remove_list = []
        remove_list = list(remove_list)
        if show_list:
            remove_list.extend(
                [key for key in dct.keys() if key not in show_list])

        for key in remove_list:
            if dct.has_key(key):
                del dct[key]


@functools.total_ordering
class Version(object):
    """API Version object."""

    string = 'X-xCAT3-API-Version'
    """HTTP Header string carrying the requested version"""

    min_string = 'X-xCAT3-API-Minimum-Version'
    """HTTP response header"""

    max_string = 'X-xCAT3-API-Maximum-Version'
    """HTTP response header"""

    def __init__(self, headers, default_version, latest_version):
        """Create an API Version object from the supplied headers.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :raises: webob.HTTPNotAcceptable
        """
        (self.major, self.minor) = Version.parse_headers(
            headers, default_version, latest_version)

    def __repr__(self):
        return '%s.%s' % (self.major, self.minor)

    @staticmethod
    def parse_headers(headers, default_version, latest_version):
        """Determine the API version requested based on the headers supplied.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :returns: a tuple of (major, minor) version numbers
        :raises: webob.HTTPNotAcceptable
        """
        version_str = headers.get(Version.string, default_version)

        if version_str.lower() == 'latest':
            parse_str = latest_version
        else:
            parse_str = version_str

        try:
            version = tuple(int(i) for i in parse_str.split('.'))
        except ValueError:
            version = ()

        if len(version) != 2:
            raise exc.HTTPNotAcceptable(_(
                "Invalid value for %s header") % Version.string)
        return version

    def __gt__(self, other):
        return (self.major, self.minor) > (other.major, other.minor)

    def __eq__(self, other):
        return (self.major, self.minor) == (other.major, other.minor)

    def __ne__(self, other):
        return not self.__eq__(other)
