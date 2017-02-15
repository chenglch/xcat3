# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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


class Conductor(Base):
    """Represents a conductor service entry."""

    __tablename__ = 'conductors'
    __table_args__ = (
        schema.UniqueConstraint('hostname', name='uniq_conductors0hostname'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), nullable=False)
    online = Column(Boolean, default=True)


class Node(Base):
    """Represents a bare metal node."""

    __tablename__ = 'nodes'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_nodes0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    mgt = Column(String(36), nullable=True)
    arch = Column(String(15), nullable=True)
    type = Column(String(15), nullable=True)
    state = Column(String(15), nullable=True)
    task_action = Column(String(20), nullable=True)
    osimage_id = Column(Integer, ForeignKey('osimage.id'), nullable=True)
    scripts_names = Column(String(255), nullable=True)
    control_info = Column(db_types.JsonEncodedDict, nullable=True)
    console_info = Column(db_types.JsonEncodedDict, nullable=True)
    reservation = Column(String(255), nullable=True)
    conductor_affinity = Column(Integer,
                                ForeignKey('conductors.id',
                                           name='nodes_conductor_affinity_fk'),
                                nullable=True)


class Nics(Base):
    """Represents a network port of a bare metal node."""

    __tablename__ = 'nics'
    __table_args__ = (
        schema.UniqueConstraint('mac', name='uniq_nics0mac'),
        schema.UniqueConstraint('uuid', name='uniq_nicss0uuid'),
        table_args())
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    mac = Column(String(18), nullable=True)
    ip = Column(String(36), nullable=True)
    netmask = Column(String(36), nullable=True)
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=True,
                     index=True)
    extra = Column(db_types.JsonEncodedDict, nullable=True)
    type = Column(String(36), nullable=True)


class Networks(Base):
    """Represents a network port of a bare metal node."""

    __tablename__ = 'networks'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_network0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    network = Column(String(36), nullable=True)
    netmask = Column(String(36), nullable=True)
    gateway = Column(String(36), nullable=True)
    dhcpserver = Column(String(255), nullable=True)
    nameservers = Column(String(255), nullable=True)
    ntpservers = Column(String(255), nullable=True)
    dynamicrange = Column(String(255), nullable=True)
    extra = Column(db_types.JsonEncodedDict, nullable=True)


class OSImage(Base):
    """Represents a Operation System image."""
    __tablename__ = 'osimage'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_osimage0name'),
        table_args())
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    profile = Column(String(36), nullable=True)
    type = Column(String(36), nullable=True)
    provmethod = Column(String(36), nullable=True)
    rootfstype = Column(String(36), nullable=True)


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
