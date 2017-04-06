import copy
import requests
import json

from oslo_log import log as logging
from xcat3.common import client_exception
from xcat3.common import utils

LOG = logging.getLogger(__name__)


class HttpClient(object):
    def __init__(self, insecure=False, http_log_debug=False, cacert=None):
        self.session = requests.Session()
        self.http_log_debug = http_log_debug
        if insecure:
            self.verify_cert = False
        else:
            if cacert:
                self.verify_cert = cacert
            else:
                self.verify_cert = True

    def http_log_req(self, method, url, kwargs):
        string_parts = ['curl -g -i']

        if not kwargs.get('verify', True):
            string_parts.append(' --insecure')

        string_parts.append(" '%s'" % url)
        string_parts.append(' -X %s' % method)

        headers = copy.deepcopy(kwargs['headers'])
        string_parts.append(' -H %s' % headers)
        string_parts.append(" '%s'" % url)

        if 'data' in kwargs:
            data = json.loads(kwargs['data'])
            string_parts.append(" -d '%s'" % json.dumps(data))

        LOG.debug("REQ: %s" % "".join(string_parts))

    def http_log_resp(self, resp):
        if not self.http_log_debug:
            return

        if resp.text and resp.status_code != 400:
            try:
                body = json.loads(resp.text)
            except ValueError:
                body = None
        else:
            body = None

        self._logger.debug("RESP: [%(status)s] %(headers)s\nRESP BODY: "
                           "%(text)s\n", {'status': resp.status_code,
                                          'headers': resp.headers,
                                          'text': json.dumps(body)})

    def request(self, method, url, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['data'] = json.dumps(kwargs.pop('body'))
        kwargs['verify'] = self.verify_cert
        self.http_log_req(method, url, kwargs)

        request_func = requests.request
        if self.session.session:
            request_func = self.session.request

        resp = request_func(
            method,
            url,
            **kwargs)

        self.http_log_resp(resp)

        if resp.text:
            if resp.status_code == 400:
                if ('Connection refused' in resp.text or
                            'actively refused' in resp.text):
                    raise client_exception.ConnectionRefused(resp.text)
            try:
                body = json.loads(resp.text)
            except ValueError:
                body = None
        else:
            body = None

        if resp.status_code >= 400:
            raise client_exception.from_response(resp, body, url, method)

        return resp, body

    def _time_request(self, url, method, **kwargs):
        with utils.record_time(self.times, self.timings, method, url):
            resp, body = self.request(url, method, **kwargs)
        return resp, body

    def get(self, url, **kwargs):
        return self._time_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._time_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self._time_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        return self._time_request(url, 'DELETE', **kwargs)
