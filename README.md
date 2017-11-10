# cloudify-libvirt-plugin
Add direct support of libvirt to cloudify, use with restrinctions.

Before use check that you have 64bit platform, if you want to start 64bit images.

based on https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/

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
sudo yum install epel-release
sudo yum install qemu-kvm libvirt-devel libvirt libvirt-python wget gcc python-devel qemu-system-x86 genisoimage
sudo service libvirtd restart
sudo groupadd libvirt
sudo usermod -a -G libvirt cfyuser
sudo usermod -a -G kvm cfyuser
```

# Types

## cloudify.libvirt.domain
Description for VM

**Supported properties:**
* `libvirt_auth`: connection url, by default: `qemu:///system`

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

**Inputs for actions:**
* `create`:
  * `params`: list of params for template, can be empty
  * `network_file`: Teplate for network. Defaults is [network.xml](cloudify_libvirt/templates/network.xml)

**Runtime properties:**
* `resource_id`: resource name.
* `params`: params used for create object.

# Relationships

## cloudify.libvirt.relationships.connected_to
Update `ip` runtime property in VM by data from network.

## Examples
* [Ubuntu:amd64 vm with connection by fabric](examples/vm_fabric.amd64.yaml)
* [Ubuntu:amd64 vm with scale support](examples/vm_agent.yaml)
* [Ubuntu:arm64 vm with connection by fabric](examples/vm_fabric.arm64.yaml)

## TODO:
* Add more examples with different vm struct and archictures: mips, powerpc
* Add tests

