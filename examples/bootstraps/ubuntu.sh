sudo apt-get update
sudo apt-get install -yq qemu-kvm qemu python-libvirt libvirt-dev qemu-system-arm genisoimage
sudo usermod -a -G libvirtd `whoami`
# cloudify part
sudo apt-get install -yq python-virtualenv python-dev git
# env create
rm -rf centos-libvirt
mkdir  centos-libvirt
virtualenv centos-libvirt
cd centos-libvirt
. bin/activate
pip install pip --upgrade
pip install https://github.com/cloudify-cosmo/cloudify-dsl-parser/archive/4.2.zip
pip install https://github.com/cloudify-cosmo/cloudify-rest-client/archive/4.2.zip
pip install https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/4.2.zip
pip install https://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.5.1.zip
pip install https://github.com/cloudify-cosmo/cloudify-cli/archive/4.2.zip
pip install https://github.com/cloudify-cosmo/cloudify-fabric-plugin/archive/1.5.1.zip
cfy init -r

git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git
pip install -e cloudify-libvirt-plugin

cfy install  cloudify-libvirt-plugin/examples/vm_fabric.amd64.yaml
