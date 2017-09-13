# cloudify-libvirt-plugin
Add direct support of libvirt to cloudify/fully unsupported thing/don't use it

based on https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/
# Before use need to install
```shell
sudo apt-get install -yq qemu-kvm qemu python-libvirt libvirt-dev libxml2-dev
sudo usermod -a -G libvirtd `whoami`
```
