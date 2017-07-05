# coding=utf-8
import os
from oslo_log import log
from oslo_config import cfg

from xcat3.common import exception
from xcat3.copycd import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF
PLUGIN_LOG = "Redhat:"

products = {
    "1480943823.812754": "centos-7.3",  # x86_64
    "1450147276.351714": "centos-7.2",  # ppc64le
    "1449699925.561114": "centos-7.2",  # x86_64
    "1427495138.035654": "centos-7.1",
    "1404489053.504589": "centos-7.0",

    "1463897259.552895": "centos-6.8",  # x86_64
    "1438724467.511049": "centos-6.7",  # x86_64
    "1414159991.958686": "centos-6.6",
    "1385726732.061157": "centos-6.5",  # x86_64
    "1362445555.957609": "centos-6.4",  # x86_64
    "1341569670.539525": "centos-6.3",  # x86
    "1323560292.885204": "centos-6.2",
    "1310229985.226287": "centos-6",

    "1381776971.473332": "centos-5.10",  # x86_64
    "1357930415.252042": "centos-5.9",  # x86_64
    "1330913492.861127": "centos-5.8",  # x86_64
    "1301444731.448392": "centos-5.6",
    "1272326751.405938": "centos-5.5",
    "1254416275.453877": "centos-5.4",  # x86_64
    "1237641529.260981": "centos-5.3",
    "1214240246.285059": "centos-5.2",
    "1213888991.267240": "centos-5.2",
    "1195929637.060433": "centos-5.1",
    "1195929648.203590": "centos-5.1",
    "1176234647.982657": "centos-5",

    "1156364963.862322": "centos-4.4",
    "1178480581.024704": "centos-4.5",
    "1195488871.805863": "centos-4.6",
    "1195487524.127458": "centos-4.6",

    "1170973598.629055": "rhelc-5",

    "1170978545.752040": "rhels-5",
    "1192660014.052098": "rhels-5.1",
    "1192663619.181374": "rhels-5.1",
    "1209608466.515430": "rhels-5.2",
    "1209603563.756628": "rhels-5.2",
    "1209597827.293308": "rhels-5.2",
    "1231287803.932941": "rhels-5.3",
    "1231285121.960246": "rhels-5.3",
    "1250668122.507797": "rhels-5.4",  # x86-64
    "1250663123.136977": "rhels-5.4",  # x86
    "1250666120.105861": "rhels-5.4",  # ppc
    "1269262918.904535": "rhels-5.5",  # ppc
    "1269260915.992102": "rhels-5.5",  # i386
    "1269263646.691048": "rhels-5.5",  # x86_64
    "1328205744.315196": "rhels-5.8",  # x86_64
    "1354216429.587870": "rhels-5.9",  # x86_64
    "1354214009.518521": "rhels-5.9",  # ppc64
    "1378846702.129847": "rhels-5.10",  # x86_64
    "1378845049.643372": "rhels-5.10",  # ppc64
    "1409145026.642170": "rhels-5.11",
    "1285193176.460470": "rhels-6",  # x86_64
    "1285192093.430930": "rhels-6",  # ppc64
    "1305068199.328169": "rhels-6.1",  # x86_64
    "1305067911.467189": "rhels-6.1",  # ppc64
    "1321546114.510099": "rhels-6.2",  # x86_64
    "1321546739.676170": "rhels-6.2",  # ppc64
    "1339641244.734735": "rhels-6.3",  # ppc64
    "1339640147.274118": "rhels-6.3",  # x86_64
    "1339638991.532890": "rhels-6.3",  # i386
    "1359576752.435900": "rhels-6.4",  # x86_64
    "1359576196.686790": "rhels-6.4",  # ppc64
    "1384196515.415715": "rhels-6.5",  # x86_64
    "1384198011.520581": "rhels-6.5",  # ppc64
    "1411733344.627228": "rhels-6.6",  # x86_64
    "1411733344.616389": "rhels-6.6",  # ppc64
    "1435823078.283602": "rhels-6.7",  # ppc64
    "1435823078.298912": "rhels-6.7",  # x86_64
    "1460645249.800975": "rhels-6.8",  # ppc64
    "1460645249.825876": "rhels-6.8",  # x86_64
    "1399449226.171922": "rhels-7",  # x86_64
    "1399449226.155578": "rhels-7",  # ppc64
    "1424360759.989976": "rhels-7.1",  # x86_64
    "1424360759.878519": "rhels-7.1",  # ppc64
    "1424361409.280138": "rhels-7.1",  # ppc64le
    "1446216863.790260": "rhels-7.2",  # x86_64
    "1446216863.764721": "rhels-7.2",  # ppc64
    "1446216863.771788": "rhels-7.2",  # ppc64le

    "1285193176.593806": "rhelhpc-6",  # x86_64
    "1305067719.718814": "rhelhpc-6.1",  # x86_64
    "1321545261.599847": "rhelhpc-6.2",  # x86_64
    "1339640148.070971": "rhelhpc-6.3",  # x86_64
    "1359576195.413831": "rhelhpc-6.4",  # x86_64, RHEL ComputeNode
    "1384196516.465862": "rhelhpc-6.5",  # x86_64, RHEL ComputeNode
    "1411733344.599861": "rhelhpc-6.6",  # x86_64, RHEL ComputeNode
    "1435823078.264564": "rhelhpc-6.7",  # x86_64, RHEL ComputeNode
    "1460645249.741799": "rhelhpc-6.8",  # x86_64, RHEL ComputeNode
    "1399449226.140088": "rhelhpc-7.0",  # x86_64, RHEL ComputeNode
    "1424360759.772760": "rhelhpc-7.1",  # x86_64, RHEL ComputeNode
    "1446216863.725127": "rhelhpc-7.2",  # x86_64, RHEL ComputeNode

    "1194015916.783841": "fedora-8",
    "1194015385.299901": "fedora-8",
    "1210112435.291709": "fedora-9",
    "1210111941.792844": "fedora-9",
    "1227147467.285093": "fedora-10",
    "1227142402.812888": "fedora-10",
    "1243981097.897160": "fedora-11",  # x86_64 DVD ISO
    "1257725234.740991": "fedora-12",  # x86_64 DVD ISO
    "1273712675.937554": "fedora-13",  # x86_64 DVD ISO
    "1287685820.403779": "fedora-14",  # x86_64 DVD ISO
    "1305315870.828212": "fedora-15",  # x86_64 DVD ISO
    "1372355769.065812": "fedora-19",  # x86_64 DVD ISO
    "1372402928.663653": "fedora-19",  # ppc64 DVD ISO
    "1386856788.124593": "fedora-20",  # x86_64 DVD ISO

    "1194512200.047708": "rhas-4.6",
    "1194512327.501046": "rhas-4.6",
    "1241464993.830723": "rhas-4.8",  # x86-64

    "1273608367.051780": "SL-5.5",  # x86_64 DVD ISO
    "1299104542.844706": "SL-6",  # x86_64 DVD ISO
    "1390839789.062069": "SL-6.5",  # x86_64 DVD ISO Install

    "1394111947.452332": "pkvm-2.1",  # ppc64, PowerKVM
    "1413749127.352649": "pkvm-2.1.1",  # ppc64, PowerKVM
};


class RedhatImage(base.Image):
    def __init__(self, path, install_dir, name):
        super(RedhatImage, self).__init__(path, install_dir, name)

    def _parse_enterprise_info(self, parts):
        if len(parts) >= 5:
            if "Pegas" in parts[4] and len(parts) > 5:
                product = "rhels-pegas"
                version = parts[5]
            else:
                product = "rhels"
                version = parts[4]
        tree_info_path = os.path.join(self.mnt_dir, '.treeinfo')
        with open(tree_info_path) as f:
            lines = f.readlines()
        for line in lines:
            if 'variant = ComputeNode' in line:
                product = "rhelhpc" % parts[4]
                version = parts[4]
                break
        return product, version

    def parse_info(self):
        dist_info_file = os.path.join(self.mnt_dir, '.discinfo')
        if not os.path.isfile(dist_info_file) or not os.access(
                dist_info_file, os.R_OK):
            LOG.debug(_("%(plugin)sCan not access path %(path)s"),
                      {'plugin': PLUGIN_LOG, 'path': dist_info_file})
            return None

        with open(dist_info_file) as f:
            id = f.readline().strip()
            desc = f.readline().strip()
            arch = f.readline().strip()
            # TODO: Do not support inspection temporarily.
            no = f.readline().strip()
            desc_parts = desc.split()

            temp = products.get(id, None)
            if temp is not None:
                product, version = temp.split('-')
            else:
                if 'Red Hat Enterprise Linux' in desc:
                    product, version = self._parse_enterprise_info(desc_parts)
                elif 'IBM_PowerKVM' in desc:
                    product = 'pkvm'
                    version = desc_parts[1]
                # TODO(chenglch): Do not support centos temprarily.
                else:
                    return None

            if arch == 'ppc':
                arch = 'ppc64'
            elif 'i.86' in arch:
                arch = 'x86'
        return {'product': product, 'version': version, 'arch': arch}

    def _get_kernel_path(self, dist_info):
        if dist_info['arch'] == 'x86_64':
            kernel = os.path.join(self.dist_path, 'images', 'pxeboot',
                                  'vmlinuz')
        elif dist_info['arch'] == 'ppc64le':
            kernel = os.path.join(self.dist_path, 'ppc', 'ppc64', 'vmlinuz')
        else:
            msg = _("Unsupported arch %s" % dist_info['arch'])
            raise exception.UnExpectedError(err=msg)

        if not os.path.isfile(kernel):
            raise exception.FileNotFound(file=kernel)
        return kernel

    def _get_initrd_path(self, dist_info):
        if dist_info['arch'] == 'x86_64':
            initrd = os.path.join(self.dist_path, 'images', 'pxeboot',
                                  'initrd.img')
        elif dist_info['arch'] == 'ppc64le':
            initrd = os.path.join(self.dist_path, 'ppc', 'ppc64', 'initrd.img')
        else:
            msg = _("Unsupported arch %s" % dist_info['arch'])
            raise exception.UnExpectedError(err=msg)

        if not os.path.isfile(initrd):
            raise exception.FileNotFound(file=initrd)
        return initrd
