#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: scp_snapshot
short_description: Manage Sangfor SCP VM snapshots
description:
  - Create or delete snapshots for a virtual machine on Sangfor Cloud Platform.
  - Idempotent — creating a snapshot with the same name is a no-op if it already exists.
  - Requires the sangfor-scp Python library (pip install sangfor-scp).
version_added: "1.0.3"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  state:
    description:
      - C(present) creates the snapshot.
      - C(absent) deletes the snapshot.
    type: str
    choices: [present, absent]
    default: present
  server_id:
    description: VM UUID. Required.
    type: str
    required: true
  snapshot_id:
    description: Snapshot UUID. Used to identify a snapshot for deletion. Takes priority over I(name) when deleting.
    type: str
  name:
    description: Snapshot name. Required when state=present.
    type: str
  description:
    description: Snapshot description.
    type: str
    default: ""
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
- name: Create a snapshot
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    state: present
    server_id: "{{ vm_id }}"
    name: "snap-before-upgrade"
    description: "Pre-upgrade snapshot"
  register: snap_result

- name: Delete a snapshot by ID
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    state: absent
    server_id: "{{ vm_id }}"
    snapshot_id: "{{ snap_result.snapshot.id }}"

- name: Delete a snapshot by name
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    state: absent
    server_id: "{{ vm_id }}"
    name: "snap-before-upgrade"
'''

RETURN = r'''
snapshot:
  description: The snapshot object from SCP API. Empty dict if snapshot was deleted.
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


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error, wait_for_task,
    SCPNotFoundError, SCPError,
)

_SNAP_BASE = "/janus/20180725/servers/{server_id}/snapshots"


def _snap_url(server_id, snapshot_id=None):
    base = _SNAP_BASE.format(server_id=server_id)
    if snapshot_id:
        return "{0}/{1}".format(base, snapshot_id)
    return base


def list_snapshots(client, server_id):
    try:
        data = client.request("GET", _snap_url(server_id))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("snapshots", data.get("items", [data]))
        return []
    except SCPNotFoundError:
        return []


def find_snapshot_by_name(client, server_id, name):
    for snap in list_snapshots(client, server_id):
        if snap.get("name") == name:
            return snap
    return None


def run_module():
    argspec = scp_argument_spec(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        server_id=dict(type='str', required=True),
        snapshot_id=dict(type='str'),
        name=dict(type='str'),
        description=dict(type='str', default=''),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        supports_check_mode=False,
    )

    client = get_client(module)
    p = module.params
    state = p['state']
    server_id = p['server_id']
    snapshot_id = p.get('snapshot_id')
    name = p.get('name')
    wait = p['wait']
    timeout = p['wait_timeout']
    result = dict(changed=False, snapshot={}, task_id=None)

    # ── absent ──────────────────────────────────────────────────────────
    if state == 'absent':
        snap = None
        if snapshot_id:
            try:
                snap = client.request("GET", _snap_url(server_id, snapshot_id))
            except SCPNotFoundError:
                module.exit_json(**result)
            except SCPError as e:
                handle_scp_error(module, e)
        elif name:
            snap = find_snapshot_by_name(client, server_id, name)
            if snap is None:
                module.exit_json(**result)
            snapshot_id = snap['id']
        else:
            module.fail_json(msg="Either 'snapshot_id' or 'name' is required when state=absent")

        try:
            resp = client.request("DELETE", _snap_url(server_id, snapshot_id))
            task_id = None
            if isinstance(resp, dict):
                task_id = resp.get('task_id')
            result['task_id'] = task_id
            if wait and task_id:
                wait_for_task(module, client, task_id, timeout)
            result['changed'] = True
        except SCPError as e:
            handle_scp_error(module, e)
        module.exit_json(**result)

    # ── present ──────────────────────────────────────────────────────────
    if not name:
        module.fail_json(msg="'name' is required when state=present")

    # Idempotency: check if snapshot already exists
    existing = find_snapshot_by_name(client, server_id, name)
    if existing:
        result['snapshot'] = existing
        module.exit_json(**result)

    try:
        body = dict(name=name, description=p.get('description', ''))
        resp = client.request("POST", _snap_url(server_id), json=body)
        task_id = None
        snap = {}
        if isinstance(resp, dict):
            task_id = resp.get('task_id')
            snap = resp
        result['task_id'] = task_id
        if wait and task_id:
            wait_for_task(module, client, task_id, timeout)
        # Try to fetch the newly created snapshot by name
        try:
            refreshed = find_snapshot_by_name(client, server_id, name)
            if refreshed:
                snap = refreshed
        except SCPError:
            pass
        result['snapshot'] = snap
        result['changed'] = True
    except SCPError as e:
        handle_scp_error(module, e)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
