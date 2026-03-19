#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_resource_pool_info
short_description: Query Sangfor SCP resource pools (AZ)
description:
  - Returns resource pool details, storage tags, and usage overview.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  az_id:
    description: Return a specific resource pool by ID. Also fetches storage tags and overview.
    type: str
  include_overview:
    description: Include resource usage overview (requires az_id).
    type: bool
    default: true
  include_storage_tags:
    description: Include storage tags (requires az_id).
    type: bool
    default: true
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
- name: List all resource pools
  erelbi.sangfor_scp.scp_resource_pool_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: pools

- name: Get a resource pool with storage tags and overview
  erelbi.sangfor_scp.scp_resource_pool_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    az_id: "{{ az_id }}"
  register: pool_detail
'''

RETURN = r'''
resource_pools:
  description: List of resource pool objects.
  type: list
  elements: dict
  returned: always
storage_tags:
  description: List of storage tags for the given az_id.
  type: list
  elements: dict
  returned: when az_id is provided
overview:
  description: Resource usage overview for the given az_id.
  type: dict
  returned: when az_id is provided
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error, SCPError,
)


def run_module():
    argspec = scp_argument_spec(
        az_id=dict(type='str'),
        include_overview=dict(type='bool', default=True),
        include_storage_tags=dict(type='bool', default=True),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    result = dict(changed=False, resource_pools=[])

    try:
        if p.get('az_id'):
            az = client.resource_pools.get(p['az_id'])
            result['resource_pools'] = [az]

            if p['include_storage_tags']:
                try:
                    result['storage_tags'] = client.resource_pools.storage_tags(p['az_id'])
                except SCPError:
                    result['storage_tags'] = []

            if p['include_overview']:
                try:
                    result['overview'] = client.resource_pools.overview(p['az_id'])
                except SCPError:
                    result['overview'] = {}
        else:
            result['resource_pools'] = list(client.resource_pools.list_all())

        module.exit_json(**result)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
