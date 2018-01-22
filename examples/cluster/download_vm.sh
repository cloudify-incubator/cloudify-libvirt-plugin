ctx logger info "Download base image ${DISK}"

cd /var/lib/libvirt/images

sudo LANG=C wget -cv "${CATALOG_URL}/${DISK}"
sudo chown qemu:libvirt

ctx instance runtime-properties vm_image "`pwd`/${DISK}"
