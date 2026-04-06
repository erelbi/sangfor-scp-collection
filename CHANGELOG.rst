=========================================
erelbi.sangfor_scp Release Notes
=========================================

.. contents:: Topics

v1.0.3
======

New Modules
-----------

- ``scp_snapshot`` — Create and delete VM snapshots (idempotent, async-aware).
- ``scp_snapshot_info`` — Query snapshots for a VM; filter by ID or name.

Minor Changes
-------------

- ``scp_server_info`` — Added ``ip`` parameter to find a VM by its IP address
  without needing a separate playbook task.

v1.0.2
======

Bugfixes
--------

- Fixed ``from __future__`` import placement in all modules — must appear before
  ``DOCUMENTATION``/``EXAMPLES``/``RETURN`` blocks to avoid ``SyntaxError`` on
  Python 3.12+ and strict interpreters.

New Playbooks
-------------

- ``playbooks/rename_server_by_ip.yml`` — rename a VM by its IP address using
  existing ``scp_server_info`` + ``scp_server`` modules.

v1.0.1
======

Bugfixes
--------

- Removed all hardcoded default values (scp_host, scp_region, scp_access_key, scp_secret_key).
  All connection parameters must now be explicitly provided via module parameters or environment variables.
- EC2 authentication now fails immediately with a clear error if scp_region is not set,
  instead of silently using the wrong region and causing authentication failures.

v1.0.0
======

New Modules
-----------

- ``scp_server`` - Manage Sangfor SCP virtual machines (CRUD + power ops)
- ``scp_server_info`` - Query virtual machines
- ``scp_server_action`` - Batch power operations on multiple VMs
- ``scp_volume`` - Manage volumes/disks (CRUD + attach/detach/resize)
- ``scp_volume_info`` - Query volumes
- ``scp_vpc`` - Manage VPC networks
- ``scp_subnet`` - Manage subnets
- ``scp_eip`` - Manage Elastic IPs (allocate/bind/unbind/release)
- ``scp_eip_info`` - Query Elastic IPs
- ``scp_image_info`` - Query images (ISO and aCloud)
- ``scp_resource_pool_info`` - Query resource pools (AZ), storage tags, overview
- ``scp_tenant_info`` - Query tenants
- ``scp_system_info`` - Query system version, platform, hosts
