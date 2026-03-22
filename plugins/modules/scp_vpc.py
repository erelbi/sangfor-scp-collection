#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r'''
---
module: scp_vpc
short_description: Manage Sangfor SCP VPC networks
description:
  - Create, update, and delete VPC networks on Sangfor Cloud Platform.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - C(present) creates or updates the VPC.
      - C(absent) deletes the VPC.
    type: str
    choices: [present, absent]
    default: present
  vpc_id:
    description: VPC UUID. Used for direct lookup.
    type: str
  name:
    description: VPC name.
    type: str
  az_id:
    description: Resource pool ID. Required when creating.
    type: str
  description:
    description: VPC description.
    type: str
    default: ""
  shared:
    description: Whether the VPC is shared across tenants (0=private, 1=shared).
    type: int
    choices: [0, 1]
    default: 0
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
- name: Create a VPC
  erelbi.sangfor_scp.scp_vpc:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: prod-vpc
    az_id: "{{ az_id }}"

- name: Delete a VPC
  erelbi.sangfor_scp.scp_vpc:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    name: prod-vpc
'''

RETURN = r'''
vpc:
  description: The VPC object.
  type: dict
  returned: always
changed:
  description: Whether any change was made.
  type: bool
  returned: always
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error,
    SCPNotFoundError, SCPError,
)


def find_vpc(client, module):
    vpc_id = module.params.get('vpc_id')
    name = module.params.get('name')
    try:
        if vpc_id:
            return client.networks.get_vpc(vpc_id)
        if name:
            for vpc in client.networks.list_vpcs():
                if vpc.get('name') == name:
                    return vpc
    except SCPNotFoundError:
        return None
    except SCPError as e:
        handle_scp_error(module, e)
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        vpc_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        description=dict(type='str', default=''),
        shared=dict(type='int', default=0, choices=[0, 1]),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        supports_check_mode=False,
        required_one_of=[['vpc_id', 'name']],
    )

    client = get_client(module)
    p = module.params
    result = dict(changed=False, vpc={})

    vpc = find_vpc(client, module)

    if p['state'] == 'absent':
        if vpc is None:
            module.exit_json(**result)
        try:
            client.networks.delete_vpc(vpc['id'])
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    if vpc is None:
        if not p.get('az_id'):
            module.fail_json(msg="az_id is required to create a VPC")
        try:
            vpc = client.networks.create_vpc(
                az_id=p['az_id'],
                name=p['name'],
                description=p.get('description', ''),
                shared=p.get('shared', 0),
            )
            result['vpc'] = vpc
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
    else:
        updates = {}
        if p.get('description') is not None and p['description'] != vpc.get('description', ''):
            updates['description'] = p['description']
        if p.get('shared') is not None and p['shared'] != vpc.get('shared'):
            updates['shared'] = p['shared']

        if updates:
            try:
                client.networks.update_vpc(vpc['id'], **updates)
                result['changed'] = True
                try:
                    result['vpc'] = client.networks.get_vpc(vpc['id'])
                except SCPError:
                    result['vpc'] = vpc
            except SCPError as e:
                handle_scp_error(module, e)
        else:
            result['vpc'] = vpc

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
