sudo yum install -y -q epel-release
sudo yum install -y -q qemu-kvm libvirt wget qemu-system-x86 genisoimage deltarpm iptables python-netifaces

sudo service libvirtd restart
sudo groupadd libvirt
sudo usermod --append --groups kvm `whoami`
sudo usermod --append --groups libvirt `whoami`

sudo service libvirtd restart
