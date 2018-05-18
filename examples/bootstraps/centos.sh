sudo yum install -y epel-release
sudo yum install -y qemu-kvm libvirt-devel libvirt libvirt-python wget gcc python-devel qemu-system-x86 genisoimage
sudo service libvirtd restart
sudo groupadd libvirt
sudo usermod --append --groups kvm `whoami`
sudo usermod --append --groups libvirt `whoami`

# cloudify part
sudo yum install -y python-virtualenv python-pip git
# env create
CREATEPATH=/opt/centos-libvirt
sudo rm -rf $CREATEPATH
sudo mkdir $CREATEPATH
sudo chmod 777 $CREATEPATH
sudo chown qemu:libvirt $CREATEPATH
virtualenv $CREATEPATH
cd $CREATEPATH
source bin/activate
pip install pip --upgrade
pip install cloudify
cfy profile use local

git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git -b master
pip install -e cloudify-libvirt-plugin

cfy install  cloudify-libvirt-plugin/examples/vm_fabric.amd64.yaml --install-plugins
