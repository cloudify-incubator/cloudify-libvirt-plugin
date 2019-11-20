sudo apt-get update
sudo apt-get install -yq qemu-kvm qemu python-libvirt libvirt-dev qemu-system-arm genisoimage
sudo usermod -a -G libvirtd `whoami`
# cloudify part
sudo apt-get install -yq python-virtualenv python-dev git python-netifaces
# env create
rm -rf centos-libvirt
mkdir  centos-libvirt
virtualenv centos-libvirt --python=python2.7
cd centos-libvirt
# install cloudify
source bin/activate
pip install pip --upgrade

# install plugins
git clone https://github.com/cloudify-incubator/cloudify-utilities-plugin.git -b master
pip install -e cloudify-utilities-plugin
git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git -b master
pip install -e cloudify-libvirt-plugin
# install cloudify
pip install cloudify==4.6
# use local install
cfy profile use local

# create vm
cfy install cloudify-libvirt-plugin/examples/vm_ubuntu.arm64.yaml --task-retry-interval=30 --task-retries=20

# desroy vm
cfy uninstall -b examples
