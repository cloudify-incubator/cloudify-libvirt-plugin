sudo apt-get update
sudo apt-get install -yq qemu-kvm qemu python-libvirt libvirt-dev qemu-system-arm genisoimage
sudo usermod -a -G libvirtd `whoami`
# cloudify part
sudo apt-get install -yq python-virtualenv python-dev git python-netifaces
# env create
rm -rf centos-libvirt
mkdir  centos-libvirt
virtualenv centos-libvirt
cd centos-libvirt
source bin/activate
pip install pip --upgrade
pip install cloudify
cfy profile use local

git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git -b master
pip install -e cloudify-libvirt-plugin

cfy install  cloudify-libvirt-plugin/examples/vm_fabric.amd64.yaml --install-plugins
