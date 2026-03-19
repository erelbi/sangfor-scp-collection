#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_server_action
short_description: Batch power operations on multiple Sangfor SCP VMs
description:
  - Performs the same power operation on a list of VMs simultaneously.
  - This module always reports changed=true when called.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  server_ids:
    description: List of VM UUIDs to operate on.
    type: list
    elements: str
    required: true
  action:
    description:
      - Power action to perform on all VMs.
      - C(start) powers on all VMs.
      - C(stop) gracefully shuts down all VMs.
      - C(poweroff) force powers off all VMs.
      - C(reboot) reboots all VMs.
      - C(suspend) suspends all VMs.
      - C(soft_delete) moves all VMs to the recycle bin.
    type: str
    required: true
    choices: [start, stop, poweroff, reboot, suspend, soft_delete]
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
- name: Stop multiple VMs at once
  erelbi.sangfor_scp.scp_server_action:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    server_ids:
      - "{{ vm1_id }}"
      - "{{ vm2_id }}"
    action: stop

- name: Soft-delete a list of VMs
  erelbi.sangfor_scp.scp_server_action:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    server_ids: "{{ vm_ids }}"
    action: soft_delete
'''

RETURN = r'''
changed:
  description: Always true when this module runs.
  type: bool
  returned: always
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error, SCPError,
)

ACTION_MAP = {
    'start': 'start_servers_action',
    'stop': 'stop_servers_action',
    'poweroff': 'poweroff_servers_action',
    'reboot': 'reboot_servers_action',
    'suspend': 'suspend_servers_action',
    'soft_delete': 'soft_del_servers_action',
}


def run_module():
    argspec = scp_argument_spec(
        server_ids=dict(type='list', elements='str', required=True),
        action=dict(type='str', required=True,
                    choices=list(ACTION_MAP.keys())),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=False)
    client = get_client(module)
    p = module.params

    try:
        client.servers.batch_action(p['server_ids'], ACTION_MAP[p['action']])
        module.exit_json(changed=True)
    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
