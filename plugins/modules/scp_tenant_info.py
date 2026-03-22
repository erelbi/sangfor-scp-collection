#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r'''
---
module: scp_tenant_info
short_description: Query Sangfor SCP tenants
description:
  - Returns a list of tenants on Sangfor Cloud Platform.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  tenant_id:
    description: Return a single tenant by ID.
    type: str
  name:
    description: Find a tenant by exact name.
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
- name: List all tenants
  erelbi.sangfor_scp.scp_tenant_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: tenants

- name: Find a tenant by name
  erelbi.sangfor_scp.scp_tenant_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: prod-tenant
  register: tenant
'''

RETURN = r'''
tenants:
  description: List of tenant objects.
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
        tenant_id=dict(type='str'),
        name=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    try:
        if p.get('tenant_id'):
            try:
                t = client.tenants.get(p['tenant_id'])
                module.exit_json(changed=False, tenants=[t])
            except SCPNotFoundError:
                module.exit_json(changed=False, tenants=[])

        if p.get('name'):
            t = client.tenants.find_by_name(p['name'])
            module.exit_json(changed=False, tenants=[t] if t else [])

        tenants = list(client.tenants.list_all())
        module.exit_json(changed=False, tenants=tenants)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
