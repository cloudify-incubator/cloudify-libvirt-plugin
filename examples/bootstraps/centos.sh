sudo yum install -y epel-release deltarpm
sudo yum install -y qemu-kvm libvirt-devel libvirt libvirt-python wget gcc python-devel qemu-system-x86 genisoimage
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
virtualenv $CREATEPATH
cd $CREATEPATH
source bin/activate
pip install pip --upgrade
pip install cloudify==4.3
cfy profile use local

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

# run real create
git clone https://github.com/cloudify-incubator/cloudify-libvirt-plugin.git -b virt-cloud
pip install -e cloudify-libvirt-plugin

cfy install cloudify-libvirt-plugin/examples/vm_ssh.amd64.yaml --install-plugins --task-retries 20  --task-retry-interval 30
