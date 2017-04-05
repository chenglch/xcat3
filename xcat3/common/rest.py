from oslo_log import log as logging
from xcat3.common import exception

import requests
import json

LOG = logging.getLogger(__name__)

class RestSession :

    def __init__(self) :
        self.session = requests.Session()

    def _request_log(self, method, url, headers, data) :
        log_string = ['curl -k']
        log_string.append(' -X %s' % method)
        log_string.append(' -H %s' % headers)
        log_string.append(" '%s'" % url)

        if data :
            log_string.append('-d %s' % data)

        LOG.info("REQ: %s" % "".join(log_string))

    def _rspcheck(self, rsp) :
        if rsp.text and rsp.status_code != 400 :
            try :
                body = json.loads(rsp.text)
            except ValueError :
                body = None
        else :
            body = None

        LOG.info("RESP: [%(status)s]\nRESP URL: %(url)s\nRESP BODY: %(text)s\n",
                {'status': rsp.status_code, 'url': rsp.url, 'text': json.dumps(body)})

        if rsp.status_code >= 400 :
            raise exception.ExceptionFromRestRsp(exception=rsp.reason)

    def request (self, method, url, headers, in_data) :
        if in_data :
            data = json.dumps(in_data)
        else :
            data = ''

        self._request_log(method, url, headers, data)

        try :
            response = self.session.request(method, url,
                                            data=data,
                                            headers=headers,
                                            verify = False)

        except requests.exceptions.ConnectionError as e :
            raise requests.exceptions.ConnectionError('Unable to connect to server')

        self._rspcheck(response)

        if method == 'GET' :
            return response.json()

