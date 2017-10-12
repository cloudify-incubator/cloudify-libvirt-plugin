ctx logger info "Download base image ${DISK}"

LANG=C wget -cv "https://cloud-images.ubuntu.com/trusty/current/${DISK}"

ctx instance runtime-properties vm_image "`pwd`/${DISK}"
