#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: scp_server
short_description: Manage Sangfor SCP virtual machines
description:
  - Create, update, rename, delete, and control power state of VMs on Sangfor Cloud Platform.
  - Idempotent — only changes VM if current state differs from desired state.
  - Requires the sangfor-scp Python library (pip install sangfor-scp).
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - Desired state of the VM.
      - C(present) creates or updates the VM.
      - C(absent) deletes the VM.
      - C(started) ensures the VM is running.
      - C(stopped) ensures the VM is stopped (graceful).
      - C(rebooted) reboots the VM.
      - C(suspended) suspends the VM.
      - C(restored) restores the VM from recycle bin.
    type: str
    choices: [present, absent, started, stopped, rebooted, suspended, restored]
    default: present
  server_id:
    description: VM UUID. Used for direct lookup. Takes priority over I(name).
    type: str
  name:
    description: VM name. Used for lookup when I(server_id) is not provided.
    type: str
  az_id:
    description: Resource pool (AZ) ID. Required when creating a new VM.
    type: str
  image_id:
    description: Image ID. Required when creating a new VM.
    type: str
  storage_tag_id:
    description: Storage tag ID. Required when creating a new VM.
    type: str
  cores:
    description: Number of vCPU cores.
    type: int
  memory_mb:
    description: Memory in megabytes.
    type: int
  sockets:
    description: Number of CPU sockets.
    type: int
    default: 1
  networks:
    description: List of network interfaces. Required when creating a VM.
    type: list
    elements: dict
    suboptions:
      vif_id:
        description: Virtual interface ID (e.g. net0).
        type: str
      vpc_id:
        description: VPC ID.
        type: str
      subnet_id:
        description: Subnet ID.
        type: str
      connect:
        description: Connect the interface (1=yes, 0=no).
        type: int
        default: 1
      model:
        description: NIC model.
        type: str
        default: virtio
  disks:
    description: List of disk definitions. If omitted, auto-derived from image.
    type: list
    elements: dict
  description:
    description: VM description.
    type: str
    default: ""
  power_on:
    description: Power on the VM after creation.
    type: bool
    default: true
  count:
    description: Number of VMs to create in batch.
    type: int
    default: 1
  delete_disks:
    description: Delete attached disks when deleting the VM.
    type: bool
    default: true
  force:
    description: Force power off or reboot without graceful shutdown.
    type: bool
    default: false
  wait:
    description: Wait for async tasks to complete.
    type: bool
    default: true
  wait_timeout:
    description: Seconds to wait for task completion.
    type: int
    default: 300
  scp_host:
    description: SCP platform URL (e.g. https://10.x.x.x). Can also be set via SCP_HOST env var.
    type: str
  scp_access_key:
    description: EC2 Access Key. Can also be set via SCP_ACCESS_KEY env var.
    type: str
    no_log: true
  scp_secret_key:
    description: EC2 Secret Key. Can also be set via SCP_SECRET_KEY env var.
    type: str
    no_log: true
  scp_region:
    description: EC2 region identifier.
    type: str
    default: cn-south-1
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
- name: Create a VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    state: present
    name: web-01
    az_id: "{{ az_id }}"
    image_id: "{{ image_id }}"
    storage_tag_id: "{{ storage_tag_id }}"
    cores: 2
    memory_mb: 2048
    networks:
      - vif_id: net0
        vpc_id: "{{ vpc_id }}"
        subnet_id: "{{ subnet_id }}"
        connect: 1
        model: virtio
  register: result

- name: Rename a VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    server_id: "{{ vm_id }}"
    name: web-01-renamed

- name: Stop a VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
    state: stopped

- name: Start a VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
    state: started

- name: Delete a VM and its disks
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
    state: absent
    delete_disks: true
'''

RETURN = r'''
server:
  description: The VM object from SCP API. Empty dict if VM was deleted.
  type: dict
  returned: always
task_id:
  description: Last async task ID. Useful when wait=false.
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

POWER_STATES = {
    'running': 'started',
    'stopped': 'stopped',
    'suspended': 'suspended',
}


def find_server(client, module):
    """Return server dict or None."""
    server_id = module.params.get('server_id')
    name = module.params.get('name')
    try:
        if server_id:
            return client.servers.get(server_id)
        if name:
            return client.servers.find_by_name(name)
    except SCPNotFoundError:
        return None
    except SCPError as e:
        handle_scp_error(module, e)
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'started', 'stopped',
                            'rebooted', 'suspended', 'restored']),
        server_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        image_id=dict(type='str'),
        storage_tag_id=dict(type='str'),
        cores=dict(type='int'),
        memory_mb=dict(type='int'),
        sockets=dict(type='int', default=1),
        networks=dict(type='list', elements='dict'),
        disks=dict(type='list', elements='dict'),
        description=dict(type='str', default=''),
        power_on=dict(type='bool', default=True),
        count=dict(type='int', default=1),
        delete_disks=dict(type='bool', default=True),
        force=dict(type='bool', default=False),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        supports_check_mode=False,
        required_one_of=[['server_id', 'name']],
    )

    client = get_client(module)
    p = module.params
    state = p['state']
    wait = p['wait']
    timeout = p['wait_timeout']
    result = dict(changed=False, server={}, task_id=None)

    server = find_server(client, module)

    # ── absent ──────────────────────────────────────────────────────────
    if state == 'absent':
        if server is None:
            module.exit_json(**result)
        try:
            task_id = client.servers.delete(server['id'], delete_disks=p['delete_disks'])
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    # ── restored ────────────────────────────────────────────────────────
    if state == 'restored':
        sid = (server or {}).get('id') or p.get('server_id')
        if not sid:
            module.fail_json(msg="server_id or name required to restore a VM")
        try:
            task_id = client.servers.restore(sid)
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    # ── present — create or update ───────────────────────────────────────
    if state == 'present':
        if server is None:
            # Create
            for req in ('az_id', 'image_id', 'storage_tag_id', 'cores', 'memory_mb', 'networks'):
                if not p.get(req):
                    module.fail_json(msg="'{0}' is required to create a VM".format(req))
            try:
                create_result = client.servers.create(
                    az_id=p['az_id'],
                    image_id=p['image_id'],
                    storage_tag_id=p['storage_tag_id'],
                    cores=p['cores'],
                    memory_mb=p['memory_mb'],
                    sockets=p['sockets'],
                    name=p['name'],
                    networks=p['networks'],
                    disks=p.get('disks'),
                    count=p['count'],
                    description=p.get('description', ''),
                    power_on=p['power_on'],
                )
                task_id = create_result.get('task_id')
                result['task_id'] = task_id
                if wait and task_id:
                    wait_for_task(module, client, task_id, timeout)
                # Fetch VM detail
                vm_ids = create_result.get('uuids', [])
                if vm_ids:
                    try:
                        result['server'] = client.servers.get(vm_ids[0])
                    except SCPError:
                        result['server'] = {'id': vm_ids[0]}
                result['changed'] = True
            except SCPError as e:
                handle_scp_error(module, e)
        else:
            # Update if anything changed
            updates = {}
            if p.get('name') and p['name'] != server.get('name'):
                updates['name'] = p['name']
            if p.get('description') is not None and p['description'] != server.get('description', ''):
                updates['description'] = p['description']
            if p.get('cores') and p['cores'] != server.get('cores'):
                updates['cores'] = p['cores']
            if p.get('memory_mb') and p['memory_mb'] != server.get('memory_mb'):
                updates['memory_mb'] = p['memory_mb']
            if p.get('sockets') and p['sockets'] != server.get('sockets'):
                updates['sockets'] = p['sockets']

            if updates:
                try:
                    task_id = client.servers.update(server['id'], **updates)
                    result['task_id'] = task_id
                    if wait and task_id:
                        wait_for_task(module, client, task_id, timeout)
                    result['changed'] = True
                    try:
                        result['server'] = client.servers.get(server['id'])
                    except SCPError:
                        result['server'] = server
                except SCPError as e:
                    handle_scp_error(module, e)
            else:
                result['server'] = server
        module.exit_json(**result)

    # ── power state transitions ──────────────────────────────────────────
    if server is None:
        module.fail_json(msg="VM not found: {0}".format(p.get('name') or p.get('server_id')))

    vm_status = server.get('status', '')
    task_id = None

    try:
        if state == 'started':
            if vm_status == 'running':
                result['server'] = server
                module.exit_json(**result)
            task_id = client.servers.start(server['id'])

        elif state == 'stopped':
            if vm_status == 'stopped':
                result['server'] = server
                module.exit_json(**result)
            task_id = client.servers.stop(server['id'], force=p['force'])

        elif state == 'rebooted':
            task_id = client.servers.reboot(server['id'], force=p['force'])

        elif state == 'suspended':
            if vm_status == 'suspended':
                result['server'] = server
                module.exit_json(**result)
            task_id = client.servers.suspend(server['id'])

        if task_id:
            result['task_id'] = task_id
            if wait:
                wait_for_task(module, client, task_id, timeout)
        result['changed'] = True
        try:
            result['server'] = client.servers.get(server['id'])
        except SCPError:
            result['server'] = server

    except SCPError as e:
        handle_scp_error(module, e)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
