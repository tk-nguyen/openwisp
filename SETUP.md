# Setting up the OpenWISP and OpenWRT infrastructure

## First, prepare 2 virtual machines:
- 1 machine running Debian 10, will be running OpenWISP
- 1 machine running OpenWRT, downloaded from https://downloads.openwrt.org/releases/21.02.0/targets/x86/64/

## Setting up OpenWISP 
### Installing OpenWISP
- Create a virtualenv named `openwisp-dev` and activate it:
```bash
$ python3 -m venv openwisp-dev
$ source openwisp-dev/bin/activate
$ cd openwisp-dev
```

- Create the `roles` and `collections` folders for ansible:
```bash
$ mkdir roles collections
```

- Create `ansible.cfg` with the following contents:
```yaml
[defaults]
roles_path=~/openwisp-dev/roles
collections_paths=~/openwisp-dev/collections
```

- Create `requirements.yml` with the following contents:
```yaml
---
roles:
  - src: https://github.com/openwisp/ansible-openwisp2.git
    version: dev
    name: openwisp.openwisp2-dev

collections:
  - name: community.general
    version: ">=3.6.0"
```

- Install requirements from `requirements.yml`:
```bash
$ ansible-galaxy install -r requirements.yml
```

- Create `hosts` with the following contents:
```ini
[openwisp2]
<IP of the Debian VM>
```

- Create `playbook.yml` with the following contents:
```yaml
- hosts: openwisp2
  become: "{{ become | default('yes') }}"
  roles:
    - openwisp.openwisp2-dev
  vars:
    openwisp2_network_topology: true
    openwisp2_firmware_upgrader: true
    openwisp2_monitoring: true # monitoring is enabled by default
    openwisp2_extra_django_settings:
        OPENWISP_USERS_AUTH_API: true
        OPENWISP_CONTROLLER_API: true
    openwisp2_time_zone: "Asia/Ho_Chi_Minh" 
```

- Run the playbook:
```bash
$ ansible-playbook -i hosts playbook.yml -k --become -K
```

- Restart `supervisor`:
```bash
sudo systemctl restart supervisor.service
```

## Setting up OpenWRT
- On the VM running OpenWRT, install `openwisp-config` and `lua-cjson`:
```bash
opkg update
opkg install http://downloads.openwisp.io/openwisp-config/latest/openwisp-config-openssl_0.6.0a-1_all.ipk
opkg install lua-cjson
```
- Edit `/etc/config/openwisp`, change `url`, `verify_ssl` and `shared_secret`:
```config
config controller 'http'
  option url '<IP of the VM running OpenWISP'
  option verify_ssl '0' # Self-signed cert
  option shared_secret '<secret, found in Organization tab of OpenWISP WebUI>'
```
![token](screenshots/token.png)
- Restart `openwisp_config`:
```bash
# /etc/init.d/openwisp_config restart
```

