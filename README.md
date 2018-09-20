# cloudify-libvirt-plugin
Add direct support of libvirt to cloudify, use with restrictions.

Before use check that you have 64bit platform, if you want to start 64bit images.

Based on https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/

Release history: [CHANGELOG.txt](CHANGELOG.txt)

# Plugin Requirements

* Python versions:
    * 2.7.x
* Packages versions:
    * libvirt-python >= 3.7.0
    * libvirt >= 1.3.1
    * qemu >= 2.5.0

# Before use on Ubuntu/Debian
```shell
sudo apt-get install -yq qemu-kvm qemu python-libvirt libvirt-dev libxml2-dev qemu-system-arm qemu-efi
sudo usermod -a -G libvirtd `whoami`
```

# Before use on CentOS
```shell
sudo yum install -y epel-release
sudo yum install -y qemu-kvm libvirt-devel libvirt libvirt-python wget gcc python-devel qemu-system-x86 genisoimage
sudo service libvirtd restart
sudo groupadd libvirt
sudo usermod -a -G libvirt cfyuser
sudo usermod -a -G kvm cfyuser
sudo usermod -a -G qemu cfyuser
```

# Types

## cloudify.libvirt.domain
Description for VM

**Supported properties:**
* `libvirt_auth`: connection url, by default: `qemu:///system`
* `backup_dir`: directory for save backups, by default: `./`

**Inputs for actions:**
* `configure`:
  * `params`: list of params for template, can be empty
  * `domain_file`: Template for domain. Defaults is [domain.xml](cloudify_libvirt/templates/domain.xml)

**Runtime properties:**
* `resource_id`: resource name.
* `params`: params used for create object.

## cloudify.libvirt.network
Description for Network

**Supported properties:**
* `libvirt_auth`: connection url, by default: `qemu:///system`
* `backup_dir`: directory for save backups, by default: `./`
* `params`: params used for create object.
  * `use_external_resource`: (optional) Use external object. The default is `false`.
  * `resource_id`: (optional) Used to identify the object when `use_external_resource` is true.
  * `dev`: Device name
  * `forwards`: settings for network `forwards`.
  * `ips`: settings for network `ips`.

**Inputs for actions:**
* `create`:
  * `params`: list of params for template, can be empty
  * `network_file`: Template for network. Defaults is [network.xml](cloudify_libvirt/templates/network.xml)

**Runtime properties:**
* `resource_id`: resource name.
* `params`: params used for create object.

# Relationships

## cloudify.libvirt.relationships.connected_to
Update `ip` runtime property in VM by data from network.

## Examples

### Without external connectivity

* [Ubuntu:amd64 vm with connection by fabric](examples/vm_ssh.amd64.yaml)
* [Ubuntu:arm64 vm with connection by fabric](examples/vm_ssh.arm64.yaml)
* [CentOS:amd64 vm with connection by fabric](examples/vm_centos.amd64.yaml)

For documentation `backup` / `restore` workflows with noncluster blueprints look to
[Utilities Plugin](https://github.com/cloudify-incubator/cloudify-utilities-plugin/blob/master/cloudify_suspend/README.md).

### With external connectivity

* [CentOS:amd64 vm with scale support](examples/vm_agent.yaml)
* [CentOS:Manager install with kubernetes nested install](examples/cluster.yaml)

Notes for use:

* Enable ssh login between manager and libvirt host without password, by call:
    ```shell
    cat examples/cluster/id_rsa.pub | ssh centos@<manager_host> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >>  ~/.ssh/authorized_keys"
    cat examples/cluster/id_rsa.pub | ssh centos@<libvirt_host> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >>  ~/.ssh/authorized_keys"
    ```

* Provide private key '/etc/cloudify/kvm.key' to manager host:
    ```shell
    cat examples/cluster/id_rsa | ssh centos@<manager_host> "cat >> ~/kvm.key && sudo mv kvm.key /etc/cloudify/kvm.key && sudo chown cfyuser:cfyuser /etc/cloudify/kvm.key && sudo chmod 400 /etc/cloudify/kvm.key
    ```

* Check that manager can connect to virthost by ssh, run on manager:
    ```shell
    sudo su cfyuser -
    ssh -i  /etc/cloudify/kvm.key centos@<libvirt_host>
    ```

* You can use any user instead 'centos' with sudo rights without password ('ALL=(ALL) NOPASSWD:ALL' in sudoers).

* Install libvirt client libraries on manager:
    ```shell
    sudo yum install -y libvirt-devel libvirt libvirt-python
    sudo service libvirtd restart
    sudo groupadd libvirt
    sudo usermod -a -G libvirt cfyuser
    sudo usermod -a -G kvm cfyuser
    sudo usermod -a -G qemu cfyuser
    ```

* Fix routing on manager for see "external ips" from libvirt host, `192.168.202.0` will be fake network for exteranl ip's.
    ```shell
    sudo route add -net 192.168.202.0 netmask 255.255.255.0 gw <libvirt_host>
    ```

* If you use openstack for host libvirt host (nested in nested virtualization) attach additional ip's to port:
    ```shell
    openstack port list | grep <libvirt_host> # search for <openstack_port_id>
    openstack port set --allowed-address ip-address=192.168.202.16 <openstack_port_id>
    openstack port set --allowed-address ip-address=192.168.202.17 <openstack_port_id>
    openstack port set --allowed-address ip-address=192.168.202.18 <openstack_port_id>
    openstack port set --allowed-address ip-address=192.168.202.19 <openstack_port_id>
    openstack port set --allowed-address ip-address=192.168.202.20 <openstack_port_id>
    ```

* Set default secrets for blueprints:
    ```shell
    cfy profile use <manager_host> -u admin -p admin -t default_tenant
    cfy secret create agent_user -u -s "cfyagent"
    cfy secret create agent_use_public_ip -u -s "true"
    cfy secret create libvirt_cluster_user -u -s "centos"
    cfy secret create libvirt_cluster_key -u -s "/etc/cloudify/kvm.key"
    cfy secret create libvirt_cluster_host -u -s <libvirt_host>
    cfy secret create libvirt_cluster_external_ip -u -s "192.168.202.16,192.168.202.17,192.168.202.18,192.168.202.19,192.168.202.20"
    cfy secret create libvirt_cluster_external_dev -u -s "eth0"
    cfy secret create agent_key_public -u -f examples/cluster/id_rsa.pub
    cfy secret create agent_key_private -u -f examples/cluster/id_rsa
    cfy secret create libvirt_common_network -u -s "manager_network"
    ```

## Wagon creation:

Recommended constraints file for CentOs 7.x and RedHat 7.x is:
```
libvirt-python==4.0.0
cloudify-plugins-common==3.3
```

You should to install [libvirt-devel](examples/bootstraps/centos.sh#L2) before create wagon.

## TODO:
* Add more examples with different vm struct and archictures: mips, powerpc
