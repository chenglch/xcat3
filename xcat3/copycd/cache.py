import os
import requests
import sendfile
import shutil
from oslo_log import log
from oslo_concurrency import lockutils

from xcat3.conf import CONF
from xcat3.common.i18n import _, _LE, _LI, _LW

LOG = log.getLogger(__name__)

def copy_image(src, dst):
    with open(src, 'r') as s:
        filesize = os.path.getsize(s.name)
        with open(dst, 'w') as d:
            sendfile.sendfile(d.fileno(), s.fileno(), 0, filesize)


def backup_iso(iso, install_dir, image):
    iso_dir = os.path.join(install_dir, 'iso')
    backup_path = os.path.join(iso_dir, '%s.iso' % image)
    if not os.path.exists(backup_path):
        print(_("Copy iso from %(src)s to %(dst)s" % {'src': iso,
                                                      'dst': backup_path}))
        copy_image(iso, backup_path)


def fetch_image(url, dst):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(dst, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)


@lockutils.synchronized('xcat3-osimage.lock', external=True)
def ensure_osimage(url, install_dir, iso_name):
    dst = os.path.join(install_dir, 'iso', iso_name)
    if not os.path.exists(dst):
        LOG.info(_LI('OSImage %(img)s do not exsit on %(host)s, '
                     'downloading...'),
                 {'host': CONF.conductor.host_ip, 'img': iso_name})
        fetch_image(url, dst)
    else:
        # ensure only one worker process enter here
        return
    from xcat3.copycd import copycds
    copycds.create(dst, None, install_dir, False)
    LOG.info(_LI('Copycd complete for iso %(iso)s'), {'iso': dst})
