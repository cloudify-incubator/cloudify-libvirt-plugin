ctx logger info "Download base image ${DISK}"

LANG=C wget -cv wget "https://cloud-images.ubuntu.com/trusty/20170919/${DISK}"

ctx instance runtime-properties vm_image "`pwd`/${DISK}"
