#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_volume
short_description: Manage Sangfor SCP volumes (disks)
description:
  - Create, delete, resize, attach, and detach volumes on Sangfor Cloud Platform.
  - Idempotent — attach/detach checks current state before acting.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - C(present) creates the volume if it doesn't exist. Resizes if size_mb is larger.
      - C(absent) deletes the volume.
      - C(attached) attaches the volume to I(server_id).
      - C(detached) detaches the volume from any server.
    type: str
    choices: [present, absent, attached, detached]
    default: present
  volume_id:
    description: Volume UUID. Takes priority over I(name).
    type: str
  name:
    description: Volume name.
    type: str
  az_id:
    description: Resource pool ID. Required when creating.
    type: str
  storage_tag_id:
    description: Storage tag ID. Required when creating.
    type: str
  size_mb:
    description: Volume size in megabytes. Required when creating.
    type: int
  description:
    description: Volume description.
    type: str
    default: ""
  preallocate:
    description: Preallocate disk space (0=thin, 1=thick).
    type: int
    choices: [0, 1]
    default: 0
  server_id:
    description: VM ID to attach/detach. Required for state=attached.
    type: str
  device_id:
    description: Device slot (e.g. ide1). Auto-assigned if omitted.
    type: str
  wait:
    description: Wait for async tasks to complete.
    type: bool
    default: true
  wait_timeout:
    description: Seconds to wait for task completion.
    type: int
    default: 300
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
- name: Create a 100 GB volume
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: data-disk-01
    az_id: "{{ az_id }}"
    storage_tag_id: "{{ storage_tag_id }}"
    size_mb: 102400

- name: Attach volume to a VM
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: attached
    volume_id: "{{ volume_id }}"
    server_id: "{{ vm_id }}"

- name: Detach volume
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: detached
    volume_id: "{{ volume_id }}"
    server_id: "{{ vm_id }}"

- name: Delete a volume
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    name: data-disk-01
'''

RETURN = r'''
volume:
  description: The volume object from SCP API.
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


def find_volume(client, module):
    volume_id = module.params.get('volume_id')
    name = module.params.get('name')
    try:
        if volume_id:
            return client.volumes.get(volume_id)
        if name:
            for v in client.volumes.list_all():
                if v.get('name') == name:
                    return v
    except SCPNotFoundError:
        return None
    except SCPError as e:
        handle_scp_error(module, e)
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'attached', 'detached']),
        volume_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        storage_tag_id=dict(type='str'),
        size_mb=dict(type='int'),
        description=dict(type='str', default=''),
        preallocate=dict(type='int', default=0, choices=[0, 1]),
        server_id=dict(type='str'),
        device_id=dict(type='str'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        supports_check_mode=False,
        required_one_of=[['volume_id', 'name']],
    )

    client = get_client(module)
    p = module.params
    state = p['state']
    wait = p['wait']
    timeout = p['wait_timeout']
    result = dict(changed=False, volume={}, task_id=None)

    volume = find_volume(client, module)

    if state == 'absent':
        if volume is None:
            module.exit_json(**result)
        try:
            task_id = client.volumes.delete(volume['id'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    if state == 'present':
        if volume is None:
            for req in ('az_id', 'storage_tag_id', 'size_mb'):
                if not p.get(req):
                    module.fail_json(msg="'{0}' is required to create a volume".format(req))
            try:
                cr = client.volumes.create(
                    az_id=p['az_id'],
                    storage_tag_id=p['storage_tag_id'],
                    size_mb=p['size_mb'],
                    name=p['name'],
                    description=p.get('description', ''),
                    preallocate=p.get('preallocate', 0),
                )
                task_id = cr.get('task_id')
                result['task_id'] = task_id
                if wait and task_id:
                    wait_for_task(module, client, task_id, timeout)
                vol_id = cr.get('volume_id')
                if vol_id:
                    try:
                        result['volume'] = client.volumes.get(vol_id)
                    except SCPError:
                        result['volume'] = {'id': vol_id}
                result['changed'] = True
            except SCPError as e:
                handle_scp_error(module, e)
        else:
            # Resize if requested size is larger
            current_size = volume.get('size_mb') or volume.get('size', 0)
            if p.get('size_mb') and p['size_mb'] > current_size:
                try:
                    task_id = client.volumes.resize(volume['id'], p['size_mb'])
                    result['task_id'] = task_id
                    if wait and task_id:
                        wait_for_task(module, client, task_id, timeout)
                    result['changed'] = True
                    try:
                        result['volume'] = client.volumes.get(volume['id'])
                    except SCPError:
                        result['volume'] = volume
                except SCPError as e:
                    handle_scp_error(module, e)
            else:
                result['volume'] = volume
        module.exit_json(**result)

    # attached / detached
    if volume is None:
        module.fail_json(msg="Volume not found: {0}".format(p.get('name') or p.get('volume_id')))

    if state == 'attached':
        if not p.get('server_id'):
            module.fail_json(msg="server_id is required for state=attached")
        current_server = volume.get('server_id')
        if current_server and current_server == p['server_id']:
            result['volume'] = volume
            module.exit_json(**result)
        try:
            task_id = client.servers.attach_volume(
                p['server_id'], volume['id'],
                device_id=p.get('device_id'),
            )
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
            try:
                result['volume'] = client.volumes.get(volume['id'])
            except SCPError:
                result['volume'] = volume
        except SCPError as e:
            handle_scp_error(module, e)

    elif state == 'detached':
        current_server = volume.get('server_id')
        if not current_server:
            result['volume'] = volume
            module.exit_json(**result)
        srv_id = p.get('server_id') or current_server
        try:
            task_id = client.servers.detach_volume(srv_id, volume['id'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
            try:
                result['volume'] = client.volumes.get(volume['id'])
            except SCPError:
                result['volume'] = volume
        except SCPError as e:
            handle_scp_error(module, e)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
