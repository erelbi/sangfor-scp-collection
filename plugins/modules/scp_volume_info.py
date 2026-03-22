#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r'''
---
module: scp_volume_info
short_description: Query Sangfor SCP volumes
description:
  - Returns a list of volumes matching the given filters.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  volume_id:
    description: Return a single volume by ID.
    type: str
  name:
    description: Filter by exact volume name.
    type: str
  az_id:
    description: Filter by resource pool ID.
    type: str
  server_id:
    description: Return volumes attached to this VM ID.
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
- name: List all volumes
  erelbi.sangfor_scp.scp_volume_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: volumes

- name: Get volumes attached to a VM
  erelbi.sangfor_scp.scp_volume_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    server_id: "{{ vm_id }}"
  register: vm_volumes
'''

RETURN = r'''
volumes:
  description: List of volume objects.
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
        volume_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        server_id=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    try:
        if p.get('volume_id'):
            try:
                vol = client.volumes.get(p['volume_id'])
                module.exit_json(changed=False, volumes=[vol])
            except SCPNotFoundError:
                module.exit_json(changed=False, volumes=[])

        if p.get('server_id'):
            vols = list(client.volumes.list_attached(p['server_id']))
            module.exit_json(changed=False, volumes=vols)

        filters = {}
        if p.get('az_id'):
            filters['az_id'] = p['az_id']

        volumes = list(client.volumes.list_all(**filters))
        if p.get('name'):
            volumes = [v for v in volumes if v.get('name') == p['name']]

        module.exit_json(changed=False, volumes=volumes)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
