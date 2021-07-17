# Setting up the OpenWISP and OpenWRT infrastructure

First, prepare 2 virtual machines:
- 1 machine running Debian 10, will be running OpenWISP
- 1 machine running OpenWRT, downloaded from [here](https://downloads.openwrt.org/releases/21.02.0-rc3/targets/x86/64/)

After installing Debian on the first VM:
- Create a folder name `openwisp`
- Clone [ansible-openwisp2](https://github.com/openwisp/ansible-openwisp2) as `openwisp.openwisp2`
- Clone [Stouts.postfix](https://github.com/nemesisdesign/Stouts.postfix)
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
    - openwisp.openwisp2
  vars:
    openwisp2_controller_pip: "https://github.com/openwisp/openwisp-controller/tarball/master"
    openwisp2_utils_pip: "https://github.com/openwisp/openwisp-utils/tarball/master#egg=openwisp-utils[rest]"
    openwisp2_users_pip: "https://github.com/openwisp/openwisp-users/tarball/master#egg=openwisp-users[rest]"
    postfix_myhostname: localhost
    openwisp2_extra_django_settings:
      OPENWISP_USERS_AUTH_API: true
      OPENWISP_CONTROLLER_API: true
    openwisp2_extra_python_packages:
      - "djangorestframework==3.12.4"
```
- Run the playbook:
```bash
$ ansible-playbook -i hosts playbook.yml -k --become -K
```
