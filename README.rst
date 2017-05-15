Test Project
============

This is just a experimental prototype for the technique discussion purpose. It
leverage the basic framework of openstack, add support to process multiple
resources per request. Currently, it only has several interface to monitor the
performance of database and eventlet green thread.

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
  gettext git rabbitmq-server mysql-server jq isc-dhcp-server ntp apache2 \
  tftpd-hpa xinetd

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
database connection string and the transport url string. For example ::

  [DEFAULT]
    rpc_response_timeout = 3600
    pecan_debug = true
    transport_url = rabbit://xcat3:cluster@11.4.40.22:5672/
    log_dir = /var/log/xcat3
    [api]
    host_ip = 11.4.40.22
    port = 3010
    max_limit = 6000
    workers = 2 # suggest: the number of cpu cores
    [database]
    connection = mysql+pymysql://xcat3:cluster@11.4.40.22/xcat3?charset=utf8
    backend = sqlalchemy

    [conductor]
    workers=2 # suggest: the number of cpu cores
    host_ip = 11.4.40.22

    [dhcp]
    omapi_secret = IetCkIN8YY5OXn/g383w0xlgVSmmda5gZpDHjMf/d0DOjS++FfhVnCm8iGi2AsHL0MWATr+8S4oa8hEA93lbxw==
    omapi_port = 7911
    omapi_server = 127.0.0.1

    [oslo_concurrency]
    lock_path = /var/lib/xcat3

Create schema for xcat3
-----------------------
::

  mkdir -p /var/log/xcat3
  mkdir -p xcat3/db/sqlalchemy/alembic/versions
  xcat3-dbsync --config-file etc/xcat3/xcat3.conf.sample create_schema

Configure xinetd and apache2 on conductor node
-----------------
::

  cp tools/config/xcat.conf.apache24 /etc/apache2/conf-available/xcat.conf.apach24
  cd /etc/apache2/conf-enabled
  ln -s ../conf-available/xcat.conf.apach24 /etc/apache2/conf-enabled/xcat.conf
  service apache2 restart
  cd -
  cp tools/config/xinetd_tftp.conf /etc/xinetd.d/tftp
  mkdir -p /var/lib/xcat3/tftpboot
  cp tools/config/tftp_map-file.conf /var/lib/xcat3/tftpboot/map-file
  service xinetd restart

NOTE: Prepare the 'pxelinux.0' file in /var/lib/xcat3/tftpboot/ directory.

Start xcat3 service
-------------------
::

  python /usr/local/bin/xcat3-api --config-file etc/xcat3/xcat3.conf.sample &
  python /usr/local/bin/xcat3-conductor --config-file etc/xcat3/xcat3.conf.sample &
  python /usr/local/bin/xcat3-network --config-file etc/xcat3/xcat3.conf.sample &

Import OSImage
----------------
::

  python /usr/local/bin/xcat3-copycds --config-file <xcat3.conf.sample> create </iso/ubuntu-16.04.1-server-amd64.iso>

Command Line  Test Example
==========================

For command usage, please see the reference
`python-xcat3client <https://github.com/chenglch/python-xcat3client>`_

All the result is from the all in one environment of x86_64 virtual machine
with 6G memory and 4 CPU cores. We can adjust the value of worker number(both
api worker and conductor worker) to improve the performance.

Create Nodes
------------
Create 9998 nodes like the following definition
::

  root@xxxxx:~/data# xcat3 show node9991
  [
    {
        "node": "node9991",
        "attr": {
            "name": "node9991",
            "reservation": null,
            "mgt": "ipmi",
            "netboot": "pxe",
            "type": null,
            "arch": "ppc64le",
            "control_info": {
                "bmc_address": "11.0.39.7",
                "bmc_password": "password",
                "bmc_username": "admin"
            },
            "console_info": {},
            "nics_info": {
                "nics": [
                    {
                        "uuid": "f8df6034-cd09-48b0-a864-116e3da1583a",
                        "name": "eth0",
                        "mac": "42:87:0a:05:27:07",
                        "ip": "12.0.39.7",
                        "extra": {
                            "primary": true
                        }
                    },
                    {
                        "uuid": "134447a7-a8ab-4f9b-9d30-833f41ee0cbe",
                        "name": "eth1",
                        "mac": "43:87:0a:05:27:07",
                        "ip": "13.0.39.7",
                        "extra": {}
                    }
                ]
            }
        }
    }
  ]

Import Nodes
------------
Import 9998 nodes with import command:
::

  time xcat3 import node9999.json (with pypy)
  node1: ok
  node2: ok
  node3: ok
  node4: ok
  ……
  node9997: ok
  node9998: ok
  Success: 9998  Total: 9998

  real   	0m11.448s
  user   	0m1.292s
  sys    	0m0.148s

It takes about 15 seconds with cpython to import about 10000 nodes, pypy
sometimes has 40% performance improvement.


Update Nodes
------------
Modify 9998 nodes with pypy
::

  time xcat3 update node[1-9999] control/bmc_username=Admin arch=x86_64 control/bmc_password=passw0rd
  node1: updated
  node10: updated
  node100: updated
  node1000: updated
  node1001: updated
  ……
  node9997: updated
  Success: 9998  Total: 9999

  real   	0m8.258s
  user   	0m0.672s
  sys    	0m0.304s

Export Nodes
------------
::

  # time xcat3 export node[1-9999] -o /tmp/node9999.json
  Export nodes data succefully.

  real   	0m4.175s
  user   	0m0.888s
  sys    	0m0.080s

Delete Nodes
------------

Delete 9998 nodes with pypy
::

  time xcat3 delete node[1-9999]
  node9999: Could not be found.
  node1: deleted
  node10: deleted
  ……

  Success: 9998  Total: 9999

  real   	0m3.253s
  user   	0m0.384s
  sys    	0m0.192s

Update network configuration to enable dhcp service
---------------------------------------------------

::

  # network
  xcat3 network-create c920 subnet=11.0.0.0 netmask=255.0.0.0 gateway=11.0.0.103   dynamic_range=11.4.40.211-11.4.40.233 nameservers=11.0.0.103


Make DHCP
---------

Generate dhcp configuration file for target nodes
::

  time xcat3 deploy node[0-9999] --state dhcp
  ……
  Success: 10000  Total: 10000

  real   	0m19.485s
  user   	0m0.165s
  sys    	0m0.065s

Clean up the dhcp or nodeset contents
::

  time xcat3 deploy node[0-9999] -d
  Success: 10000  Total: 10000

  real   	0m13.151s
  user   	0m0.165s
  sys    	0m0.065s

Deploy OSImage on VM
--------------------
::

    root@xxxxx# xcat3 create --mgt kvm --netboot pxe --arch x86_64 --nic \
    mac=52:54:00:ee:29:78,ip=11.5.102.63,primary=True \
    --control ssh_username=root,ssh_virt_type=virsh,ssh_address=11.5.102.1,ssh_key_filename=/root/.ssh/id_rsa \
    xcat3test3

    root@xxxxx# xcat3 show xcat3test3
    [
        {
            "node": "xcat3test3",
            "attr": {
                "conductor_affinity": null,
                "console_info": {},
                "name": "xcat3test3",
                "type": null,
                "netboot": "pxe",
                "state": null,
                "control_info": {
                    "ssh_username": "root",
                    "ssh_virt_type": "virsh",
                    "ssh_address": "11.5.102.1",
                    "ssh_key_filename": "/root/.ssh/id_rsa"
                },
                "mgt": "kvm",
                "reservation": null,
                "arch": "x86_64",
                "nics_info": {
                    "nics": [
                        {
                            "ip": "11.5.102.63",
                            "mac": "52:54:00:ee:29:78",
                            "extra": {
                                "primary": true
                            },
                            "uuid": "0256abbe-d8eb-4e08-9a16-43165b69dab9",
                            "name": null
                        }
                    ]
                }
            }
        }
    ]
    root@xxxxx# xcat3 deploy xcat3test[1-3] --osimage Ubuntu-Server16.04.1-x86_64
    root@xxxxx# xcat3 power xcat3test[1-3] on

    # after about 15 minutes
    root@xxxxx# ssh xcat3test3
