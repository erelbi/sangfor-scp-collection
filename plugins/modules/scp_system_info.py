#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_system_info
short_description: Query Sangfor SCP system information
description:
  - Returns platform version, host list, and system information.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  include_hosts:
    description: Include physical host list.
    type: bool
    default: true
  include_platform:
    description: Include platform info.
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
- name: Get system information
  erelbi.sangfor_scp.scp_system_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: sysinfo

- name: Print SCP version
  debug:
    msg: "SCP version: {{ sysinfo.version.build_version }}"
'''

RETURN = r'''
version:
  description: SCP build version info.
  type: dict
  returned: always
platform:
  description: Platform info dict.
  type: dict
  returned: when include_platform is true
hosts:
  description: List of physical host objects.
  type: list
  elements: dict
  returned: when include_hosts is true
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error, SCPError,
)


def run_module():
    argspec = scp_argument_spec(
        include_hosts=dict(type='bool', default=True),
        include_platform=dict(type='bool', default=True),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    result = dict(changed=False)

    try:
        result['version'] = client.system.version()
    except SCPError as e:
        handle_scp_error(module, e)

    if p['include_platform']:
        try:
            result['platform'] = client.system.platform_info()
        except SCPError:
            result['platform'] = {}

    if p['include_hosts']:
        try:
            result['hosts'] = list(client.system.list_all_hosts())
        except SCPError:
            result['hosts'] = []

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
