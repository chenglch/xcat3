import json
import sys


def gen_data(n=10):
    nodes = {"nodes": []}
    names = {"nodes": []}
    num = [0, 0]

    for i in xrange(n):
        d = dict()
        num[0] = i / 256
        num[1] = i % 256
        d['name'] = 'node%d' % i
        name = {'name': d['name']}
        d['mgt'] = 'ipmi'
        d['netboot'] = 'pxe'
        d['arch'] = 'x86_64' if i % 2 == 0 else 'ppc64le'
        d['control_info'] = {
            'bmc_address': '11.0.%d.%d' % (num[0], num[1]),
            'bmc_username': 'admin', 'bmc_password': 'password'}
        d['nics_info'] = {
            'nics': [{'mac': '42:87:0a:05:%02x:%02x' % (num[0], num[1]),
                      'ip': '12.0.%d.%d' % (num[0], num[1]),
                      'name': 'eth0',
                      'primary': True},
                     {'mac': '43:87:0a:05:%02x:%02x' % (num[0], num[1]),
                      'ip': '13.0.%d.%d' % (num[0], num[1]),
                      'name': 'eth1',
                      }],
            }

        nodes['nodes'].append(d)
        names['nodes'].append(name)

    d = dict()
    d['name'] = 'xcat3test1'
    d['mgt'] = 'kvm'
    d['netboot'] = 'pxe'
    d['arch'] = 'x86_64'
    d['control_info'] = {'ssh_username': 'root', 'ssh_virt_type': 'virsh',
                         'ssh_address': '10.5.102.1',
                         'ssh_key_filename': '/root/.ssh/id_rsa'}
    d['nics_info'] = {'nics': [
        {'mac': '52:54:00:36:ac:b1', 'ip': '10.5.102.60', 'primary': True}]}
    nodes['nodes'].append(d)
    names['nodes'].append({'name':d['name']})

    d = dict()
    d['name'] = 'xcat3test2'
    d['mgt'] = 'kvm'
    d['netboot'] = 'pxe'
    d['arch'] = 'x86_64'
    d['control_info'] = {'ssh_username': 'root', 'ssh_virt_type': 'virsh',
                         'ssh_address': '10.5.102.1',
                         'ssh_key_filename': '/root/.ssh/id_rsa'}
    d['nics_info'] = {'nics': [
        {'mac': '52:54:00:0b:0f:97', 'ip': '10.5.102.60', 'primary': True}]}
    nodes['nodes'].append(d)
    names['nodes'].append({'name': d['name']})

    return json.dumps(names), json.dumps(nodes)


def write_to_file(path, contents):
    with open(path, 'w') as f:
        f.write(contents)


if __name__ == "__main__":
    count = 3
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    if count > 65535:
        print "The max count is 65535"
        count = 65535
    names, nodes = gen_data(count)
    write_to_file('name.json', names)
    write_to_file('data.json', nodes)
