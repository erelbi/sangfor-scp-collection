# erelbi.sangfor_scp

[![Ansible Galaxy](https://img.shields.io/badge/galaxy-erelbi.sangfor__scp-blue)](https://galaxy.ansible.com/ui/repo/published/erelbi/sangfor_scp/)

Ansible Collection for managing **Sangfor Cloud Platform (SCP)** resources.

Wraps the [`sangfor-scp`](https://pypi.org/project/sangfor-scp/) Python library to provide
idempotent modules for virtual machines, volumes, networks, EIPs, snapshots, and platform information.

---

## Requirements

- Ansible >= 2.14
- Python >= 3.8
- `sangfor-scp` Python library

```bash
pip install sangfor-scp
```

---

## Installation

```bash
ansible-galaxy collection install erelbi.sangfor_scp
```

Or add to your `requirements.yml`:

```yaml
collections:
  - name: erelbi.sangfor_scp
    version: ">=1.0.0"
```

---

## Authentication

All modules accept the same auth parameters. You can pass them directly or use environment variables.

### EC2 Authentication (Recommended)

```yaml
- erelbi.sangfor_scp.scp_server_info:
    scp_host: "https://10.x.x.x"
    scp_access_key: "your_access_key"
    scp_secret_key: "your_secret_key"
    scp_region: "cn-south-1"
```

Or via environment variables:

```bash
export SCP_HOST=https://10.x.x.x
export SCP_ACCESS_KEY=your_access_key
export SCP_SECRET_KEY=your_secret_key
export SCP_REGION=cn-south-1
```

### Token Authentication

```yaml
- erelbi.sangfor_scp.scp_server_info:
    scp_host: "https://10.x.x.x"
    scp_username: "admin"
    scp_password: "your_password"
```

---

## Modules

| Module | Description |
|---|---|
| `scp_server` | Manage VMs: create, update, rename, delete, power ops |
| `scp_server_info` | Query VMs; filter by name, status, AZ, tenant, or **IP address** |
| `scp_server_action` | Batch power operations on multiple VMs |
| `scp_snapshot` | **Create and delete VM snapshots** (idempotent, async-aware) |
| `scp_snapshot_info` | **Query snapshots** for a VM; filter by ID or name |
| `scp_volume` | Manage volumes: create, delete, resize, attach, detach |
| `scp_volume_info` | Query volumes |
| `scp_vpc` | Manage VPC networks |
| `scp_subnet` | Manage subnets |
| `scp_eip` | Manage Elastic IPs: allocate, bind, unbind, release |
| `scp_eip_info` | Query Elastic IPs |
| `scp_image_info` | Query images (ISO and aCloud) |
| `scp_resource_pool_info` | Query resource pools, storage tags, usage overview |
| `scp_tenant_info` | Query tenants |
| `scp_system_info` | Query system version, platform, physical hosts |

---

## Usage Examples

### Get System Info

```yaml
- name: Get SCP system info
  erelbi.sangfor_scp.scp_system_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
  register: sysinfo

- debug:
    msg: "SCP version: {{ sysinfo.version.build_version }}"
```

### List All VMs

```yaml
- name: List all running VMs
  erelbi.sangfor_scp.scp_server_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    status: running
  register: running_vms

- debug:
    msg: "{{ item.name }} — {{ item.status }}"
  loop: "{{ running_vms.servers }}"
```

### Create a VM

```yaml
- name: Create a VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: web-01
    az_id: "{{ az_id }}"
    image_id: "{{ image_id }}"
    storage_tag_id: "{{ storage_tag_id }}"
    cores: 2
    memory_mb: 4096
    networks:
      - vif_id: net0
        vpc_id: "{{ vpc_id }}"
        subnet_id: "{{ subnet_id }}"
        connect: 1
        model: virtio
    power_on: true
    wait: true
    wait_timeout: 300
  register: new_vm

- debug:
    msg: "VM created: {{ new_vm.server.id }}"
```

### Rename a VM

```yaml
- name: Rename VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    server_id: "{{ vm_id }}"
    name: web-01-prod
```

### Stop and Start a VM

```yaml
- name: Stop VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
    state: stopped

- name: Start VM
  erelbi.sangfor_scp.scp_server:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    name: web-01
    state: started
```

### Create and Attach a Volume

```yaml
- name: Create 100 GB data volume
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: data-disk-01
    az_id: "{{ az_id }}"
    storage_tag_id: "{{ storage_tag_id }}"
    size_mb: 102400
  register: volume

- name: Attach volume to VM
  erelbi.sangfor_scp.scp_volume:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: attached
    volume_id: "{{ volume.volume.id }}"
    server_id: "{{ vm_id }}"
```

### Find VM by IP Address

```yaml
- name: Find VM by IP
  erelbi.sangfor_scp.scp_server_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    ip: "10.10.10.50"
  register: vm_by_ip

- debug:
    msg: "VM: {{ vm_by_ip.servers[0].name }} ({{ vm_by_ip.servers[0].id }})"
  when: vm_by_ip.servers | length > 0
```

### Create a Snapshot

```yaml
- name: Create snapshot before upgrade
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    server_id: "{{ vm_id }}"
    name: "snap-before-upgrade"
    description: "Pre-upgrade snapshot"
    wait: true
  register: snap_result

- debug:
    msg: "Snapshot ID: {{ snap_result.snapshot.id }}"
```

### List Snapshots for a VM

```yaml
- name: List all snapshots
  erelbi.sangfor_scp.scp_snapshot_info:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    server_id: "{{ vm_id }}"
  register: snap_list

- debug:
    msg: "{{ item.name }} — {{ item.id }}"
  loop: "{{ snap_list.snapshots }}"
```

### Delete a Snapshot

```yaml
# Delete by snapshot ID
- name: Delete snapshot by ID
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    server_id: "{{ vm_id }}"
    snapshot_id: "{{ snap_result.snapshot.id }}"

# Delete by snapshot name
- name: Delete snapshot by name
  erelbi.sangfor_scp.scp_snapshot:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: absent
    server_id: "{{ vm_id }}"
    name: "snap-before-upgrade"
```

### Batch Power Operations

```yaml
- name: Stop multiple VMs
  erelbi.sangfor_scp.scp_server_action:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    server_ids: "{{ groups['web_servers'] | map(attribute='vm_id') | list }}"
    action: stop
```

### Allocate and Bind an EIP

```yaml
- name: Allocate EIP
  erelbi.sangfor_scp.scp_eip:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    az_id: "{{ az_id }}"
    bandwidth_mb: 100
  register: eip

- name: Bind EIP to VM
  erelbi.sangfor_scp.scp_eip:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: bound
    eip_id: "{{ eip.eip.id }}"
    server_id: "{{ vm_id }}"
```

### Create VPC and Subnet

```yaml
- name: Create VPC
  erelbi.sangfor_scp.scp_vpc:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: prod-vpc
    az_id: "{{ az_id }}"
  register: vpc

- name: Create subnet
  erelbi.sangfor_scp.scp_subnet:
    scp_host: "{{ scp_host }}"
    scp_access_key: "{{ scp_ak }}"
    scp_secret_key: "{{ scp_sk }}"
    state: present
    name: app-subnet
    vpc_id: "{{ vpc.vpc.id }}"
    az_id: "{{ az_id }}"
    cidr: 192.168.10.0/24
    gateway_ip: 192.168.10.1
```

---

## Using a vars file for credentials

Create `group_vars/all/scp_auth.yml`:

```yaml
scp_host: "https://10.x.x.x"
scp_ak: "your_access_key"
scp_sk: "your_secret_key"
scp_region: "cn-south-1"
```

Encrypt with Ansible Vault:

```bash
ansible-vault encrypt group_vars/all/scp_auth.yml
```

---

## SCP Version Compatibility

| SCP Version | Support |
|---|---|
| 6.3.0+ | Full VM, Volume, Network, EIP APIs |
| 6.8.0+ | EIP APIs |
| 6.11.1+ | Snapshot APIs, latest API (tested) |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Related Projects

- [sangfor-scp Python library](https://pypi.org/project/sangfor-scp/) — underlying API client
- [GitHub](https://github.com/erelbi/sangfor-scp) — Python library source
