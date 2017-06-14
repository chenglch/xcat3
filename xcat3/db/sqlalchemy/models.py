# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Updated 2017 for xcat test purpose
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

"""
SQLAlchemy models for baremetal data.
"""

from oslo_db import options as db_options
from oslo_db.sqlalchemy import models
from oslo_db.sqlalchemy import types as db_types
import six.moves.urllib.parse as urlparse
from sqlalchemy import Boolean, Column, DateTime, Index
from sqlalchemy import ForeignKey, Integer
from sqlalchemy import schema, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm

from xcat3.common import paths
from xcat3.conf import CONF

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('xcat3.sqlite')

db_options.set_defaults(CONF, _DEFAULT_SQL_CONNECTION, 'xcat3.sqlite')


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class XCATBase(models.TimestampMixin,
               models.ModelBase):
    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative_base(cls=XCATBase)


class Service(Base):
    """Represents a conductor service entry."""

    __tablename__ = 'services'
    __table_args__ = (
        schema.UniqueConstraint('hostname', 'type',
                                name='uniq_services0hostname'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), nullable=False)
    type = Column(String(255), default='conductor')
    workers = Column(Integer)
    online = Column(Boolean, default=True)


class Node(Base):
    """Represents a bare metal node."""

    __tablename__ = 'nodes'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_nodes0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    mgt = Column(String(16))
    netboot = Column(String(16))
    arch = Column(String(16), nullable=True)
    type = Column(String(16), nullable=True)
    state = Column(String(16), nullable=True)
    task_action = Column(String(20), nullable=True)
    osimage_id = Column(Integer, ForeignKey('osimage.id'), nullable=True)
    passwd_id = Column(Integer, ForeignKey('passwd.id'),nullable=True)
    scripts_names = Column(String(255), nullable=True)
    control_info = Column(db_types.JsonEncodedDict, nullable=True)
    console_info = Column(db_types.JsonEncodedDict, nullable=True)
    nics_config = Column(db_types.JsonEncodedDict, nullable=True)
    reservation = Column(String(255), nullable=True)
    conductor_affinity = Column(Integer,
                                ForeignKey('services.id',
                                           name='nodes_conductor_affinity_fk'),
                                nullable=True)
    nics = orm.relationship(
        "Nics",
        backref='node',
        primaryjoin='and_(Nics.node_id == Node.id)',
    )


class Nics(Base):
    """Represents a network port of a bare metal node."""

    __tablename__ = 'nics'
    __table_args__ = (
        schema.UniqueConstraint('mac', name='uniq_nics0mac'),
        schema.UniqueConstraint('uuid', name='uniq_nicss0uuid'),
        table_args())
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(18))
    mac = Column(String(18), nullable=True)
    ip = Column(String(36), nullable=True)
    netmask = Column(String(36), nullable=True)
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=True,
                     index=True)
    primary = Column(Boolean, default=False)
    extra = Column(db_types.JsonEncodedDict, nullable=True)


class Networks(Base):
    """Represents a network port of a bare metal node."""

    __tablename__ = 'networks'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_network0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    subnet = Column(String(36))
    netmask = Column(String(36), nullable=True)
    gateway = Column(String(36), nullable=True)
    nameservers = Column(String(255), nullable=True)
    ntpservers = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True)
    dynamic_range = Column(String(255), nullable=True)
    extra = Column(db_types.JsonEncodedDict, nullable=True)


class DHCP(Base):
    """Represents the dhcp configuration for each host"""
    __tablename__ = 'dhcp'
    name = Column(String(255), primary_key=True)
    opts = Column(db_types.JsonEncodedDict, nullable=True)


class OSImage(Base):
    """Represents a Operation System image."""
    __tablename__ = 'osimage'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_osimage0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    arch = Column(String(16), nullable=False)
    ver = Column(String(16), nullable=False)
    distro = Column(String(16), nullable=False)
    profile = Column(String(36), nullable=True)
    type = Column(String(36), nullable=True)
    provmethod = Column(String(36), nullable=True)
    rootfstype = Column(String(36), nullable=True)
    orig_name = Column(String(255), nullable=True)


class Passwd(Base):
    """Represents password."""
    __tablename__ = 'passwd'
    __table_args__ = (
        schema.UniqueConstraint('key', name='uniq_passwd0key'),
        table_args())
    id = Column(Integer, primary_key=True)
    key = Column(String(16), nullable=False)
    username = Column(String(36), nullable=True)
    password = Column(String(255), nullable=True)
    crypt_method = Column(String(16), nullable=True)


class Script(Base):
    """Represents scripts after os deployment"""
    __tablename__ = 'scripts'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_scripts0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    post = Column(String(255), nullable=True)
    postboot = Column(String(255), nullable=True)
