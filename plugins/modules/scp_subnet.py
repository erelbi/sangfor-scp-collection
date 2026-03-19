#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_subnet
short_description: Manage Sangfor SCP subnets
description:
  - Create and delete subnets within a VPC on Sangfor Cloud Platform.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - C(present) creates the subnet if it doesn't exist.
      - C(absent) deletes the subnet.
    type: str
    choices: [present, absent]
    default: present
  subnet_id:
    description: Subnet UUID. Used for direct lookup.
    type: str
  name:
    description: Subnet name.
    type: str
  vpc_id:
    description: VPC ID. Required when creating.
    type: str
  az_id:
    description: Resource pool ID. Required when creating.
    type: str
  cidr:
    description: CIDR block (e.g. 192.168.1.0/24). Required when creating.
    type: str
  gateway_ip:
    description: Gateway IP address.
    type: str
  description:
    description: Subnet description.
    type: str
    default: ""
  dns_nameservers:
    description: List of DNS server IPs.
    type: list
    elements: str
  scp_host:
    description: SCP platform URL.
    type: str
  scp_access_key:
    description: EC2 Access Key.
    type: str
    no_log: true
  scp_secret_key:
    description: EC2 Secret Key.
    type: str
    no_log: true
  scp_region:
    description: EC2 region.
    type: str
  scp_username:
    description: Username for Token-based authentication.
    type: str
  scp_password:
    description: Password for Token-based authentication.
    type: str
    no_log: true
  scp_verify_ssl:
    description: Verify SSL certificate.
    type: bool
    default: false
  scp_timeout:
    description: HTTP request timeout in seconds.
    type: int
    default: 30
'''

EXAMPLES = r'''
- name: Create a subnet
  erelbi.sangfor_scp.scp_subnet:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: app-subnet
    vpc_id: "{{ vpc_id }}"
    az_id: "{{ az_id }}"
    cidr: 192.168.10.0/24
    gateway_ip: 192.168.10.1

- name: Delete a subnet
  erelbi.sangfor_scp.scp_subnet:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    subnet_id: "{{ subnet_id }}"
'''

RETURN = r'''
subnet:
  description: The subnet object.
  type: dict
  returned: always
changed:
  description: Whether any change was made.
  type: bool
  returned: always
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error,
    SCPNotFoundError, SCPError,
)


def find_subnet(client, module):
    subnet_id = module.params.get('subnet_id')
    name = module.params.get('name')
    vpc_id = module.params.get('vpc_id')
    try:
        if subnet_id:
            return client.networks.get_subnet(subnet_id)
        if name:
            kwargs = {}
            if vpc_id:
                kwargs['vpc_id'] = vpc_id
            for s in client.networks.list_subnets(**kwargs):
                if s.get('name') == name:
                    return s
    except SCPNotFoundError:
        return None
    except SCPError as e:
        handle_scp_error(module, e)
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        subnet_id=dict(type='str'),
        name=dict(type='str'),
        vpc_id=dict(type='str'),
        az_id=dict(type='str'),
        cidr=dict(type='str'),
        gateway_ip=dict(type='str'),
        description=dict(type='str', default=''),
        dns_nameservers=dict(type='list', elements='str'),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        supports_check_mode=False,
        required_one_of=[['subnet_id', 'name']],
    )

    client = get_client(module)
    p = module.params
    result = dict(changed=False, subnet={})

    subnet = find_subnet(client, module)

    if p['state'] == 'absent':
        if subnet is None:
            module.exit_json(**result)
        try:
            client.networks.delete_subnet(subnet['id'])
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    if subnet is None:
        for req in ('vpc_id', 'az_id', 'cidr'):
            if not p.get(req):
                module.fail_json(msg="'{0}' is required to create a subnet".format(req))
        try:
            kwargs = dict(
                vpc_id=p['vpc_id'],
                az_id=p['az_id'],
                cidr=p['cidr'],
                name=p['name'],
                description=p.get('description', ''),
            )
            if p.get('gateway_ip'):
                kwargs['gateway_ip'] = p['gateway_ip']
            if p.get('dns_nameservers'):
                kwargs['dns_nameservers'] = p['dns_nameservers']
            result['subnet'] = client.networks.create_subnet(**kwargs)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
    else:
        result['subnet'] = subnet

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
