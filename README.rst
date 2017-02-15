Test Project
============

This is just a experimental prototype for the technique discussion purpose. It
leverage the basic framework of openstack, add support to process multiple
resources per request. Currently, it only has several interface to monitor the
performance of database and eventlet green thread. Do no care about the name
**xcat3** as I can not come up with a appropriate name for it temporarily.

Process Service Model
=====================

* xcat3-api: Can be looked as a controller node which receive the request from
  client. It provide rest api interface with pecan and oslo.service.
* xcat3-conductor: Can be looked as a worker node act as a consumer of mesage
  queue to process the requests. (support multiple worker nodes)
* xcat3-network: (TODO) Manage the dhcp service for target subnet.
* console-server: conserver or confluent.

Supported operating systems:

* Ubuntu 14.04, 16.04

Pre-install steps
=================

::

  apt-get update && apt-get install build-essential python-dev libssl-dev \
  python-pip libmysqlclient-dev libxml2-dev libxslt-dev libpq-dev libffi-dev \
  gettext git rabbitmq-server mysql-server jq

Installation
============

Package
-------
::

  git clone https://github.com/chenglch/xcat3.git
  cd xcat3
  pip install -r requirements.txt
  python setup.py develop

Database
--------

Modify `/etc/mysql/my.cnf` or `/etc/mysql/mysql.conf.d/mysqld.cnf` as
follows ::


  bind-address            = 127.0.0.1   --> bind-address = 0.0.0.0

Restart mysql service ::

  service mysql restart

Grant access for xcat3 database
::

  DATABASE_USER=xcat3
  DATABASE_PASSWORD=cluster # assume the password for root is 'cluster' when setup mysql-server with apt

  mysql -uroot -h localhost -p$DATABASE_PASSWORD -e'create database xcat3'
  mysql -uroot -p$DATABASE_PASSWORD -hlocalhost -e "GRANT ALL PRIVILEGES ON xcat3.* TO '$DATABASE_USER'@'%' identified by '$DATABASE_PASSWORD';"

RabbitMQ
--------

Create rabbit user for rabbitmq ::

  user=xcat3
  pass=cluster
  rabbitmqctl add_user "$user" "$pass"
  rabbitmqctl set_permissions "$user" ".*" ".*" ".*"

Start Service
=============

Edit ``etc/xcat3/xcat3.conf.sample`` to match your environment. Especially
database connection string and the transport url string.

Create schema for xcat3
-----------------------
::

  mkdir -p /var/log/xcat3
  mkdir -p xcat3/db/sqlalchemy/alembic/versions
  xcat3-dbsync --config-file etc/xcat3/xcat3.conf.sample create_schema

Start xcat3 service
-------------------
::

  python /usr/local/bin/xcat3-api --config-file etc/xcat3/xcat3.conf.sample &
  python /usr/local/bin/xcat3-conductor --config-file etc/xcat3/xcat3.conf.sample &

Test Example
============

Rest API Example
----------------

Create Node
::

  curl -XPOST 'http://localhost:3010/v1/nodes' -H Content-Type:application/json  -d '{"nodes":[{"name":"test_xcat3", "nics_info": {"nics":[{"ip": "12.0.0.0", "mac": "42:87:0a:05:65:0", "type": "primary"}, {"ip": "13.0.0.0", "mac": "43:87:0a:05:65:0"}] } }]}'

  {
    "error": 0,
    "success": 1,
    "nodes": {
        "test_xcat3": "ok"
    }
  }
  curl -XPOST 'http://localhost:3010/v1/nodes' -H Content-Type:application/json  -d '{"nodes":[{"name":"test_xcat4"}, {"name":"test_xcat5"}]}' | jq .
  {
    "error": 0,
    "success": 2,
    "nodes": {
        "test_xcat4": "ok",
        "test_xcat5": "ok"
    }
  }

List Nodes
::

  curl -XGET 'http://localhost:3010/v1/nodes' -H Content-Type:application/json  | jq .
  {
    "nodes": [
        {
            "name": "test_xcat3"
        },
        {
            "name": "test_xcat4"
        },
        {
            "name": "test_xcat5"
        }
    ]
  }

Show Node
::

  curl -XGET 'http://localhost:3010/v1/nodes/test_xcat3' -H Content-Type:application/json  | jq .
  {
    "nics_info": {
        "nics": [
            {
                "extra": {},
                "uuid": "153c7c44-cd55-468c-a8d6-2963451c47d9",
                "mac": "42:87:0a:05:65:0"
            },
            {
                "extra": {},
                "uuid": "15f30064-1a6d-462c-8e0f-f384e5afd48c",
                "mac": "43:87:0a:05:65:0"
            }
        ]
    },
    "type": null,
    "console_info": {},
    "name": "test_xcat3",
    "arch": null,
    "created_at": "2017-03-17T05:52:03+00:00",
    "updated_at": null,
    "control_info": {},
    "mgt": null,
    "reservation": null
  }

Modify Node
::

  curl -XPATCH 'http://localhost:3010/v1/nodes/test_xcat3' -H Content-Type:application/json -d '[{"op":"add", "path": "/arch", "value": "ppc64le"}, {"op":"add", "path": "/mgt", "value": "ipmi"}]' | jq .
  {
    "nics_info": {
        "nics": [
            {
                "extra": {},
                "uuid": "153c7c44-cd55-468c-a8d6-2963451c47d9",
                "mac": "42:87:0a:05:65:0"
            },
            {
                "extra": {},
                "uuid": "15f30064-1a6d-462c-8e0f-f384e5afd48c",
                "mac": "43:87:0a:05:65:0"
            }
        ]
    },
    "type": null,
    "console_info": {},
    "name": "test_xcat3",
    "arch": "ppc64le",
    "created_at": "2017-03-17T05:52:03+00:00",
    "updated_at": "2017-03-17T06:01:47.203561+00:00",
    "control_info": {},
    "mgt": "ipmi",
    "reservation": null
  }

Power on Nodes
::

  curl -XPUT 'http://localhost:3010/v1/nodes/states/power?target=on' -H Content-Type:application/json -d '{"nodes":[{"name":"test_xcat3"}, {"name":"test_xcat4"}]}' | jq .
  {
    "nodes": {
        "test_xcat3": "ok",
        "test_xcat4": "plugin for None could not been loaded."
    }
  }

Delete Nodes
::

  curl -XDELETE 'http://localhost:3010/v1/nodes' -H Content-Type:application/json  -d '{"nodes":[{"name":"test_xcat3"}, {"name":"test_xcat4"}]}' | jq .
  {
    "nodes": {
        "test_xcat3": "deleted",
        "test_xcat4": "deleted"
    }
  }

Performance Example
-------------------
::

  cd examples
  python create_nodes.py 1000  # generated json for 1000 nodes
  time ./node_time.sh 10  # run commands above 10 times for GET and PUT, 1 time for POST and DELETE
