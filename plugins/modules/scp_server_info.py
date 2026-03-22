#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r'''
---
module: scp_server_info
short_description: Query Sangfor SCP virtual machines
description:
  - Returns a list of VMs matching the given filters.
  - This module never changes state (changed is always false).
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  server_id:
    description: Return a single VM by ID.
    type: str
  name:
    description: Filter by exact VM name.
    type: str
  az_id:
    description: Filter by resource pool ID.
    type: str
  status:
    description: Filter by VM status (running, stopped, error, ...).
    type: str
  tenant_id:
    description: Filter by tenant ID.
    type: str
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
- name: List all VMs
  erelbi.sangfor_scp.scp_server_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: all_vms

- name: List running VMs in a resource pool
  erelbi.sangfor_scp.scp_server_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    az_id: "{{ az_id }}"
    status: running
  register: running_vms

- name: Get a specific VM by name
  erelbi.sangfor_scp.scp_server_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
  register: vm_info
'''

RETURN = r'''
servers:
  description: List of VM objects.
  type: list
  elements: dict
  returned: always
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error,
    SCPNotFoundError, SCPError,
)


def run_module():
    argspec = scp_argument_spec(
        server_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        status=dict(type='str'),
        tenant_id=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    try:
        if p.get('server_id'):
            try:
                vm = client.servers.get(p['server_id'])
                module.exit_json(changed=False, servers=[vm])
            except SCPNotFoundError:
                module.exit_json(changed=False, servers=[])

        filters = {}
        for key in ('az_id', 'status', 'tenant_id'):
            if p.get(key):
                filters[key] = p[key]

        servers = list(client.servers.list_all(**filters))

        if p.get('name'):
            servers = [s for s in servers if s.get('name') == p['name']]

        module.exit_json(changed=False, servers=servers)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
