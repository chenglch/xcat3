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
        d['arch'] = 'x86_64' if i % 2 == 0 else 'ppc64le'
        d['control_info'] = {
            'ipmi_address': '11.0.%d.%d' % (num[0], num[1]),
            'ipmi_user': 'admin', 'ipmi_password': 'password'}
        d['nics_info'] = {
            'nics': [{'mac': '42:87:0a:05:%02x:%02x' % (num[0], num[1]),
                      'ip': '12.0.%d.%d' % (num[0], num[1]),
                      'primary': True},
                     {'mac': '43:87:0a:05:%02x:%02x' % (num[0], num[1]),
                      'ip': '12.0.%d.%d' % (num[0], num[1])
                      }]}

        nodes['nodes'].append(d)
        names['nodes'].append(name)
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
