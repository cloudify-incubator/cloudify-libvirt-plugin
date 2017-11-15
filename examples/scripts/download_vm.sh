ctx logger info "Download base image ${DISK}"

LANG=C wget -cv "${CATALOG_URL}/${DISK}"

ctx instance runtime-properties vm_image "`pwd`/${DISK}"
