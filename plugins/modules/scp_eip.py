#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_eip
short_description: Manage Sangfor SCP Elastic IPs
description:
  - Allocate, bind, unbind, update, and release Elastic IPs.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - C(present) allocates the EIP if it doesn't exist.
      - C(absent) unbinds and releases the EIP.
      - C(bound) binds the EIP to I(server_id).
      - C(unbound) unbinds the EIP.
    type: str
    choices: [present, absent, bound, unbound]
    default: present
  eip_id:
    description: EIP UUID.
    type: str
  az_id:
    description: Resource pool ID. Required when allocating.
    type: str
  bandwidth_mb:
    description: Bandwidth in Mbps.
    type: int
    default: 100
  description:
    description: EIP description.
    type: str
    default: ""
  server_id:
    description: VM ID to bind. Required for state=bound.
    type: str
  wait:
    description: Wait for async tasks.
    type: bool
    default: true
  wait_timeout:
    description: Seconds to wait.
    type: int
    default: 120
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
- name: Allocate an EIP
  erelbi.sangfor_scp.scp_eip:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    az_id: "{{ az_id }}"
    bandwidth_mb: 100
  register: eip

- name: Bind EIP to a VM
  erelbi.sangfor_scp.scp_eip:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: bound
    eip_id: "{{ eip.eip.id }}"
    server_id: "{{ vm_id }}"

- name: Release an EIP
  erelbi.sangfor_scp.scp_eip:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    eip_id: "{{ eip_id }}"
'''

RETURN = r'''
eip:
  description: The EIP object.
  type: dict
  returned: always
task_id:
  description: Last async task ID.
  type: str
  returned: when a task was triggered
changed:
  description: Whether any change was made.
  type: bool
  returned: always
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error, wait_for_task,
    SCPNotFoundError, SCPError,
)


def find_eip(client, module):
    eip_id = module.params.get('eip_id')
    if not eip_id:
        return None
    try:
        return client.eips.get(eip_id)
    except SCPNotFoundError:
        return None
    except SCPError as e:
        handle_scp_error(module, e)
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'bound', 'unbound']),
        eip_id=dict(type='str'),
        az_id=dict(type='str'),
        bandwidth_mb=dict(type='int', default=100),
        description=dict(type='str', default=''),
        server_id=dict(type='str'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=120),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=False)
    client = get_client(module)
    p = module.params
    state = p['state']
    wait = p['wait']
    timeout = p['wait_timeout']
    result = dict(changed=False, eip={}, task_id=None)

    eip = find_eip(client, module)

    if state == 'absent':
        if eip is None:
            module.exit_json(**result)
        try:
            # Unbind first if bound
            if eip.get('server_id'):
                task_id = client.eips.unbind(eip['id'])
                if wait and task_id:
                    wait_for_task(module, client, task_id, timeout)
            task_id = client.eips.release(eip['id'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    if state == 'present':
        if eip is None:
            if not p.get('az_id'):
                module.fail_json(msg="az_id is required to allocate an EIP")
            try:
                eip = client.eips.allocate(
                    az_id=p['az_id'],
                    bandwidth_mb=p['bandwidth_mb'],
                    description=p.get('description', ''),
                )
                result['eip'] = eip
                result['changed'] = True
            except SCPError as e:
                handle_scp_error(module, e)
        else:
            # Update bandwidth if different
            current_bw = eip.get('bandwidth_mb') or eip.get('bandwidth', 0)
            if p['bandwidth_mb'] and p['bandwidth_mb'] != current_bw:
                try:
                    task_id = client.eips.update_bandwidth(eip['id'], p['bandwidth_mb'])
                    result['task_id'] = task_id
                    if wait and task_id:
                        wait_for_task(module, client, task_id, timeout)
                    result['changed'] = True
                    try:
                        result['eip'] = client.eips.get(eip['id'])
                    except SCPError:
                        result['eip'] = eip
                except SCPError as e:
                    handle_scp_error(module, e)
            else:
                result['eip'] = eip
        module.exit_json(**result)

    if eip is None:
        module.fail_json(msg="EIP not found. Provide eip_id.")

    if state == 'bound':
        if not p.get('server_id'):
            module.fail_json(msg="server_id is required for state=bound")
        if eip.get('server_id') == p['server_id']:
            result['eip'] = eip
            module.exit_json(**result)
        try:
            task_id = client.eips.bind(eip['id'], server_id=p['server_id'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
            try:
                result['eip'] = client.eips.get(eip['id'])
            except SCPError:
                result['eip'] = eip
        except SCPError as e:
            handle_scp_error(module, e)

    elif state == 'unbound':
        if not eip.get('server_id'):
            result['eip'] = eip
            module.exit_json(**result)
        try:
            task_id = client.eips.unbind(eip['id'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
            try:
                result['eip'] = client.eips.get(eip['id'])
            except SCPError:
                result['eip'] = eip
        except SCPError as e:
            handle_scp_error(module, e)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
