#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: scp_snapshot_info
short_description: Query Sangfor SCP VM snapshots
description:
  - Returns snapshots for a given virtual machine on Sangfor Cloud Platform.
  - This module never changes state (changed is always false).
  - Requires the sangfor-scp Python library (pip install sangfor-scp).
version_added: "1.0.3"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  server_id:
    description: VM UUID. Required.
    type: str
    required: true
  snapshot_id:
    description: Return a single snapshot by ID.
    type: str
  name:
    description: Filter snapshots by exact name.
    type: str
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
- name: List all snapshots for a VM
  erelbi.sangfor_scp.scp_snapshot_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    server_id: "{{ vm_id }}"
  register: snap_list

- name: Get a specific snapshot by ID
  erelbi.sangfor_scp.scp_snapshot_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    server_id: "{{ vm_id }}"
    snapshot_id: "{{ snapshot_id }}"
  register: snap_detail

- name: Find snapshot by name
  erelbi.sangfor_scp.scp_snapshot_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    scp_region: "{{ scp_region }}"
    server_id: "{{ vm_id }}"
    name: "snap-before-upgrade"
  register: snap_info
'''

RETURN = r'''
snapshots:
  description: List of snapshot objects for the given VM.
  type: list
  elements: dict
  returned: always
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.erelbi.sangfor_scp.plugins.module_utils.scp_client import (
    scp_argument_spec, get_client, handle_scp_error,
    SCPNotFoundError, SCPError,
)

_SNAP_BASE = "/janus/20180725/servers/{server_id}/snapshots"


def _snap_url(server_id, snapshot_id=None):
    base = _SNAP_BASE.format(server_id=server_id)
    if snapshot_id:
        return "{0}/{1}".format(base, snapshot_id)
    return base


def run_module():
    argspec = scp_argument_spec(
        server_id=dict(type='str', required=True),
        snapshot_id=dict(type='str'),
        name=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params
    server_id = p['server_id']

    try:
        if p.get('snapshot_id'):
            try:
                snap = client.request("GET", _snap_url(server_id, p['snapshot_id']))
                module.exit_json(changed=False, snapshots=[snap] if snap else [])
            except SCPNotFoundError:
                module.exit_json(changed=False, snapshots=[])

        data = client.request("GET", _snap_url(server_id))
        if isinstance(data, list):
            snapshots = data
        elif isinstance(data, dict):
            snapshots = data.get("snapshots", data.get("items", []))
            if not isinstance(snapshots, list):
                snapshots = [data]
        else:
            snapshots = []

        if p.get('name'):
            snapshots = [s for s in snapshots if s.get('name') == p['name']]

        module.exit_json(changed=False, snapshots=snapshots)

    except SCPNotFoundError:
        module.exit_json(changed=False, snapshots=[])
    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
