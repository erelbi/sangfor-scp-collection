#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_eip_info
short_description: Query Sangfor SCP Elastic IPs
description:
  - Returns a list of EIPs matching the given filters.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  eip_id:
    description: Return a single EIP by ID.
    type: str
  az_id:
    description: Filter by resource pool ID.
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
- name: List all EIPs
  erelbi.sangfor_scp.scp_eip_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: eips
'''

RETURN = r'''
eips:
  description: List of EIP objects.
  type: list
  elements: dict
  returned: always
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error,
    SCPNotFoundError, SCPError,
)


def run_module():
    argspec = scp_argument_spec(
        eip_id=dict(type='str'),
        az_id=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    try:
        if p.get('eip_id'):
            try:
                eip = client.eips.get(p['eip_id'])
                module.exit_json(changed=False, eips=[eip])
            except SCPNotFoundError:
                module.exit_json(changed=False, eips=[])

        filters = {}
        if p.get('az_id'):
            filters['az_id'] = p['az_id']

        eips = list(client.eips.list_all(**filters))
        module.exit_json(changed=False, eips=eips)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
