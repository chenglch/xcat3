import json
import sys
import requests

headers = {'Content-Type': 'application/json'}


def create_data():
    net = {}
    net['name'] = 'install'
    net['subnet'] = '10.0.0.0'
    net['netmask'] = '255.0.0.0'
    net['gateway'] = '10.0.0.103'
    net['dhcpserver'] = '10.4.40.22'
    resp = requests.post('http://localhost:3010/v1/network', headers=headers,
                         data=json.dumps(net))
    print resp
    net = {}
    net['name'] = 'local'
    net['subnet'] = '127.0.0.0'
    net['netmask'] = '255.0.0.0'
    net['gateway'] = '192.0.0.103'
    net['dhcpserver'] = '192.4.40.22'
    resp = requests.post('http://localhost:3010/v1/network', headers=headers,
                         data=json.dumps(net))
    print resp


def remove_data():
    resp = requests.delete('http://localhost:3010/v1/network/install',
                           headers=headers)
    print resp
    resp = requests.delete('http://localhost:3010/v1/network/local',
                           headers=headers)
    print resp


if __name__ == "__main__":
    action = 'post'
    if len(sys.argv) > 1:
        action = str(sys.argv[1])
    if action == 'post':
        create_data()
    elif action == 'remove':
        remove_data()
    else:
        print 'Invalid argument'
