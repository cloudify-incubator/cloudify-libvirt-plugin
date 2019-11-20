sudo yum install -q -y epel-release deltarpm
sudo yum install -q -y qemu-kvm libvirt-devel libvirt libvirt-python wget gcc python-devel qemu-system-x86 genisoimage qemu-system-arm
sudo service libvirtd restart
sudo groupadd libvirt
sudo usermod --append --groups kvm `whoami`
sudo usermod --append --groups libvirt `whoami`
sudo usermod --append --groups qemu `whoami`

# check nested virtualization
virt-host-validate

# cloudify part
sudo yum install -y python-virtualenv python-pip git python-netifaces

# env create
CREATEPATH=/opt/centos-libvirt
sudo rm -rf $CREATEPATH
sudo mkdir $CREATEPATH
sudo chmod 777 $CREATEPATH
sudo chown qemu:libvirt $CREATEPATH
virtualenv $CREATEPATH --python=python2.7
cd $CREATEPATH
source bin/activate
pip install pip --upgrade

# enable zram, better to enable, we will run many hungry hosts
git clone https://github.com/mystilleef/FedoraZram.git
sudo cp FedoraZram/{zramstart,zramstat,zramstop} /usr/sbin/
sudo chown root:root /usr/sbin/zram*
sudo chmod 755 /usr/sbin/zram*

sudo cp FedoraZram/mkzram.service /lib/systemd/system
sudo chown root:root /lib/systemd/system/mkzram.service
sudo chmod 644 /lib/systemd/system/mkzram.service

sudo cp FedoraZram/zram /etc/sysconfig
sudo chown root:root /etc/sysconfig/zram
sudo chmod 644 /etc/sysconfig/zram

sudo systemctl daemon-reload
sudo systemctl enable mkzram.service
sudo systemctl start mkzram.service

# install plugins
git clone https://github.com/cloudify-incubator/cloudify-utilities-plugin.git -b master
pip install -e cloudify-utilities-plugin
git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git -b master
pip install -e cloudify-libvirt-plugin
# install cloudify
pip install cloudify==4.6
# use local install
cfy profile use local

# create arm vm
cfy install cloudify-libvirt-plugin/examples/vm_ubuntu.arm64.yaml --task-retry-interval=30 --task-retries=20 -b arm_ubuntu -vv
sleep 3600
cfy uninstall -b arm_ubuntu

# create x86 vm
cfy install cloudify-libvirt-plugin/examples/vm_centos.amd64.yaml --task-retry-interval=30 --task-retries=20 -b x86_centos -vv
sleep 3600
cfy uninstall -b x86_centos

