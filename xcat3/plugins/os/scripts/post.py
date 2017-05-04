# -*- encoding: utf-8 -*-

import sys
import os
import httplib
import logging
import urllib2
import ssl
import socket
import subprocess
import traceback
import json

DEFAULT_HTTP_TIMEOUT = 10  # seconds
LOG_PATH = '/var/log/xcat3/post.log'

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] '
                           '%(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=LOG_PATH,
                    filemode='a')
LOG = logging.getLogger(__name__)


class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    def __init__(self, key=None, cert=None, ca_certs=None):
        urllib2.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert
        self.ca_certs = ca_certs

    def https_open(self, req):
        return self.do_open(self.get_connection, req)

    def get_connection(self, host, timeout=DEFAULT_HTTP_TIMEOUT):
        return HTTPSConnection(host, key_file=self.key, cert_file=self.cert,
                               timeout=timeout, ca_certs=self.ca_certs)


class HTTPSConnection(httplib.HTTPSConnection):
    def __init__(self, host, **kwargs):
        self.ca_certs = kwargs.pop('ca_certs', None)
        httplib.HTTPSConnection.__init__(self, host, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = ssl.wrap_socket(sock, keyfile=self.key_file,
                                    certfile=self.cert_file,
                                    ca_certs=self.ca_certs)


class HttpsRestClient(object):
    def __init__(self, cert_key=None, cert_pem=None, ca_certs=None):
        self.cert_key = cert_key
        self.cert_pem = cert_pem
        self.ca_certs = ca_certs
        self.handlers = [
            HTTPSClientAuthHandler(key=self.cert_key, cert=self.cert_pem,
                                   ca_certs=self.ca_certs), ]

    def get(self, url, data):
        request = urllib2.Request(url, json.dumps(data))
        request.add_header("Content-Type", 'application/json')
        request.get_method = lambda: 'GET'
        urllib2.install_opener(request)
        resp = urllib2.urlopen(url)
        if int(resp.code) > 400:
            raise
        return resp.read()

    def put(self, url, data=None):
        request = urllib2.Request(url, json.dumps(data))
        request.add_header("Content-Type", 'application/json')
        request.get_method = lambda: 'PUT'
        resp = urllib2.urlopen(request)
        if int(resp.code) > 400:
            raise
        return resp.read()

    def post(self, url, data):
        # data = urllib.urlencode(data)
        request = urllib2.Request(url, json.dumps(data))
        request.add_header("Content-Type", 'application/json')
        resp = urllib2.urlopen(request)
        if int(resp.code) > 400:
            raise
        return resp.read()

    def delete(self, url):
        request = urllib2.Request(url)
        request.get_method = lambda: 'DELETE'
        resp = urllib2.urlopen(request)
        if int(resp.code) > 400:
            raise
        return resp.read()


class Utils(object):
    @staticmethod
    def execute(cmd, **kwargs):
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, **kwargs)
            out, err = p.communicate()
            LOG.info('Running command %s out: %s err: %s' % (
                ' '.join(cmd), out, err))
        except subprocess.CalledProcessError, OSError:
            LOG.exception('Error to running command: %s err: %s' % (
                ' '.join(cmd), traceback.format_exc()))

    @staticmethod
    def retry(count=3):
        def _wrap(func):
            def wrap(*args, **kwargs):
                times = 0
                excp = None
                while times < count:
                    try:
                        ret = func(*args, **kwargs)
                    except Exception as e:
                        times += 1
                        excp = e
                    else:
                        return ret
                if excp is not None:
                    raise excp

            return wrap

        return _wrap

    @staticmethod
    def wrap_try(excp=Exception):
        def _wrap(func):
            def wrap(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except excp:
                    LOG.exception(traceback.format_exc())

            return wrap

        return _wrap


@Utils.retry(count=3)
def _fetch_ssh_pub(host, port, node):
    url = 'http://%s:%s/nodes/provision/callback?name=%s' % (host, port, node)
    action = {'fetch_ssh_pub': 'root'}
    client = HttpsRestClient()
    data = client.put(url, action)
    data = json.loads(data)
    return data['pub_key']


@Utils.wrap_try()
def setup_ssh_key(host, port, node):
    pub_key = _fetch_ssh_pub(host, port, node)
    try:
        os.makedirs('/root/.ssh')
    except OSError:
        pass
    with open('/root/.ssh/authorized_keys', 'a') as f:
        f.write(pub_key)


@Utils.wrap_try()
def setup_grub_config():
    if not os.path.exists('/boot/grub/grub.cfg'):
        return
    with open('/proc/cmdline') as f:
        kcmdline = f.read().strip('\n')

    karg = kcmdline[kcmdline.find('console='):]
    new_lines = []
    with open('/etc/default/grub', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            if line.find("GRUB_CMDLINE_LINUX_DEFAULT") != -1:
                default = line.split('\"')[1]
                line = "GRUB_CMDLINE_LINUX_DEFAULT=\"%s %s\"\n" % (
                    default, karg)
            new_lines.append(line)
        f.seek(0)
        f.truncate()
        f.writelines(new_lines)

    cmd = ['/usr/sbin/update-grub']
    Utils.execute(cmd)


@Utils.wrap_try()
@Utils.retry(count=3)
def complete_callback(host, port, node):
    client = HttpsRestClient()
    url = 'http://%s:%s/nodes/provision/callback?name=%s' % (host, port, node)
    client.put(url)


def main():
    if len(sys.argv) < 3:
        print 'Unsupported argument'
        sys.exit(1)

    host = sys.argv[1]
    port = sys.argv[2]
    node = sys.argv[3]

    setup_ssh_key(host, port, node)
    setup_grub_config()

    # NOTE(chenglch):no matter what error happens before, we should run
    # this script to avoid of repeat installation.
    complete_callback(host, port, node)


if __name__ == '__main__':
    sys.exit(main())
