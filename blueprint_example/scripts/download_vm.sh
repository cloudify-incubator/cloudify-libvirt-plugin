ctx logger info "Download base image"
LANG=C wget -cv wget https://cloud-images.ubuntu.com/trusty/20170919/trusty-server-cloudimg-amd64-disk1.img

ctx instance runtime-properties vm_image "`pwd`/trusty-server-cloudimg-amd64-disk1.img"
