# Copyright 2015 Red Hat, Inc.
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

import ast
import netaddr
import six

from oslo_versionedobjects import fields as object_fields

from xcat3.common import utils


class IntegerField(object_fields.IntegerField):
    pass


class UUIDField(object_fields.UUIDField):
    pass


class StringField(object_fields.StringField):
    pass


class StringAcceptsCallable(object_fields.String):
    @staticmethod
    def coerce(obj, attr, value):
        if callable(value):
            value = value()
        return super(StringAcceptsCallable, StringAcceptsCallable).coerce(
            obj, attr, value)


class DateTimeField(object_fields.DateTimeField):
    pass


class BooleanField(object_fields.BooleanField):
    pass


class ListOfStringsField(object_fields.ListOfStringsField):
    pass


class ObjectField(object_fields.ObjectField):
    pass


class FlexibleDict(object_fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if isinstance(value, six.string_types):
            value = ast.literal_eval(value)
        return dict(value)


class FlexibleDictField(object_fields.AutoTypedField):
    AUTO_TYPE = FlexibleDict()

    # TODO(lucasagomes): In our code we've always translated None to {},
    # this method makes this field to work like this. But probably won't
    # be accepted as-is in the oslo_versionedobjects library
    def _null(self, obj, attr):
        if self.nullable:
            return {}
        super(FlexibleDictField, self)._null(obj, attr)


class EnumField(object_fields.EnumField):
    pass


class MACAddress(object_fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        return utils.validate_and_normalize_mac(value)


class MACAddressField(object_fields.AutoTypedField):
    AUTO_TYPE = MACAddress()



class StringPattern(object_fields.FieldType):
    def get_schema(self):
        if hasattr(self, "PATTERN"):
            return {'type': ['string'], 'pattern': self.PATTERN}
        else:
            msg = _("%s has no pattern") % self.__class__.__name__
            raise AttributeError(msg)


class IPAddress(StringPattern):
    @staticmethod
    def coerce(obj, attr, value):
        try:
            return netaddr.IPAddress(value)
        except netaddr.AddrFormatError as e:
            raise ValueError(six.text_type(e))

    def from_primitive(self, obj, attr, value):
        return self.coerce(obj, attr, value)

    @staticmethod
    def to_primitive(obj, attr, value):
        return str(value)


class IPV4Address(IPAddress):
    @staticmethod
    def coerce(obj, attr, value):
        result = IPAddress.coerce(obj, attr, value)
        if result.version != 4:
            raise ValueError(_('Network "%(val)s" is not valid '
                               'in field %(attr)s') %
                             {'val': value, 'attr': attr})
        return result

    def get_schema(self):
        return {'type': ['string'], 'format': 'ipv4'}


class IPV6Address(IPAddress):
    @staticmethod
    def coerce(obj, attr, value):
        result = IPAddress.coerce(obj, attr, value)
        if result.version != 6:
            raise ValueError(_('Network "%(val)s" is not valid '
                               'in field %(attr)s') %
                             {'val': value, 'attr': attr})
        return result

    def get_schema(self):
        return {'type': ['string'], 'format': 'ipv6'}


class IPV4AndV6Address(IPAddress):
    @staticmethod
    def coerce(obj, attr, value):
        result = IPAddress.coerce(obj, attr, value)
        if result.version != 4 and result.version != 6:
            raise ValueError(_('Network "%(val)s" is not valid '
                               'in field %(attr)s') %
                             {'val': value, 'attr': attr})
        return value

    def get_schema(self):
        return {'oneOf': [IPV4Address().get_schema(),
                          IPV6Address().get_schema()]}


class IPNetwork(IPAddress):
    @staticmethod
    def coerce(obj, attr, value):
        try:
            return netaddr.IPNetwork(value)
        except netaddr.AddrFormatError as e:
            raise ValueError(six.text_type(e))


class IPV4Network(IPNetwork):

    PATTERN = (r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-'
               r'9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/([0-9]|[1-2]['
               r'0-9]|3[0-2]))$')

    @staticmethod
    def coerce(obj, attr, value):
        try:
            return netaddr.IPNetwork(value, version=4)
        except netaddr.AddrFormatError as e:
            raise ValueError(six.text_type(e))


class IPV6Network(IPNetwork):

    def __init__(self, *args, **kwargs):
        super(IPV6Network, self).__init__(*args, **kwargs)
        self.PATTERN = self._create_pattern()

    @staticmethod
    def coerce(obj, attr, value):
        try:
            return netaddr.IPNetwork(value, version=6)
        except netaddr.AddrFormatError as e:
            raise ValueError(six.text_type(e))

    def _create_pattern(self):
        ipv6seg = '[0-9a-fA-F]{1,4}'
        ipv4seg = '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'

        return (
            # Pattern based on answer to
            # http://stackoverflow.com/questions/53497/regular-expression-that-matches-valid-ipv6-addresses
            '^'
            # 1:2:3:4:5:6:7:8
            '(' + ipv6seg + ':){7,7}' + ipv6seg + '|'
            # 1:: 1:2:3:4:5:6:7::
            '(' + ipv6seg + ':){1,7}:|'
            # 1::8 1:2:3:4:5:6::8 1:2:3:4:5:6::8
            '(' + ipv6seg + ':){1,6}:' + ipv6seg + '|'
            # 1::7:8 1:2:3:4:5::7:8 1:2:3:4:5::8
            '(' + ipv6seg + ':){1,5}(:' + ipv6seg + '){1,2}|'
            # 1::6:7:8 1:2:3:4::6:7:8 1:2:3:4::8
            '(' + ipv6seg + ':){1,4}(:' + ipv6seg + '){1,3}|'
            # 1::5:6:7:8 1:2:3::5:6:7:8 1:2:3::8
            '(' + ipv6seg + ':){1,3}(:' + ipv6seg + '){1,4}|'
            # 1::4:5:6:7:8 1:2::4:5:6:7:8 1:2::8
            '(' + ipv6seg + ':){1,2}(:' + ipv6seg + '){1,5}|' +
            # 1::3:4:5:6:7:8 1::3:4:5:6:7:8 1::8
            ipv6seg + ':((:' + ipv6seg + '){1,6})|'
            # ::2:3:4:5:6:7:8 ::2:3:4:5:6:7:8 ::8 ::
            ':((:' + ipv6seg + '){1,7}|:)|'
            # fe80::7:8%eth0 fe80::7:8%1
            'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|'
            # ::255.255.255.255 ::ffff:255.255.255.255 ::ffff:0:255.255.255.255
            '::(ffff(:0{1,4}){0,1}:){0,1}'
            '(' + ipv4seg + '\.){3,3}' +
            ipv4seg + '|'
            # 2001:db8:3:4::192.0.2.33 64:ff9b::192.0.2.33
            '(' + ipv6seg + ':){1,4}:'
            '(' + ipv4seg + '\.){3,3}' +
            ipv4seg +
            # /128
            '(\/(d|dd|1[0-1]d|12[0-8]))$'
            )


class IPAddressField(object_fields.AutoTypedField):
    AUTO_TYPE = IPAddress()


class IPV4AddressField(object_fields.AutoTypedField):
    AUTO_TYPE = IPV4Address()


class IPV6AddressField(object_fields.AutoTypedField):
    AUTO_TYPE = IPV6Address()


class IPV4AndV6AddressField(object_fields.AutoTypedField):
    AUTO_TYPE = IPV4AndV6Address()


class IPNetworkField(object_fields.AutoTypedField):
    AUTO_TYPE = IPNetwork()


class IPV4NetworkField(object_fields.AutoTypedField):
    AUTO_TYPE = IPV4Network()


class IPV6NetworkField(object_fields.AutoTypedField):
    AUTO_TYPE = IPV6Network()