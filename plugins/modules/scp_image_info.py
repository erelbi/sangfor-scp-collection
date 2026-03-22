#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r'''
---
module: scp_image_info
short_description: Query Sangfor SCP images
description:
  - Returns available images (ISO and aCloud) from Sangfor Cloud Platform.
  - This module never changes state.
version_added: "1.0.0"
author: erelbi
requirements:
  - python >= 3.8
  - sangfor-scp >= 0.2.0
options:
  image_id:
    description: Return a single image by ID.
    type: str
  name:
    description: Filter by exact image name.
    type: str
  az_id:
    description: Filter by resource pool ID.
    type: str
  image_type:
    description: Filter by image type.
    type: str
    choices: [iso, acloud, all]
    default: all
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
- name: List all images
  erelbi.sangfor_scp.scp_image_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: images

- name: List only aCloud images in a resource pool
  erelbi.sangfor_scp.scp_image_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    az_id: "{{ az_id }}"
    image_type: acloud
  register: acloud_images

- name: Find image by name
  erelbi.sangfor_scp.scp_image_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: "Ubuntu-22.04"
  register: ubuntu_image
'''

RETURN = r'''
images:
  description: List of image objects.
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
        image_id=dict(type='str'),
        name=dict(type='str'),
        az_id=dict(type='str'),
        image_type=dict(type='str', default='all', choices=['iso', 'acloud', 'all']),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)
    client = get_client(module)
    p = module.params

    try:
        if p.get('image_id'):
            try:
                img = client.images.get(p['image_id'])
                module.exit_json(changed=False, images=[img])
            except SCPNotFoundError:
                module.exit_json(changed=False, images=[])

        filters = {}
        if p.get('az_id'):
            filters['az_id'] = p['az_id']

        image_type = p.get('image_type', 'all')
        if image_type == 'iso':
            images = list(client.images.list_iso(**filters))
        elif image_type == 'acloud':
            images = list(client.images.list_acloud(**filters))
        else:
            images = list(client.images.list_all(**filters))

        if p.get('name'):
            images = [i for i in images if i.get('name') == p['name']]

        module.exit_json(changed=False, images=images)

    except SCPError as e:
        handle_scp_error(module, e)


def main():
    run_module()


if __name__ == '__main__':
    main()
