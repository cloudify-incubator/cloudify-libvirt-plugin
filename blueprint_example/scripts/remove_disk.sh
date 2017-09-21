DISK=`ctx instance runtime-properties vm_image`
ctx logger info "Will be deleted ${DISK}"
rm -rf "${DISK}"

DISK=`ctx instance runtime-properties vm_cloudinit`
ctx logger info "Will be deleted ${DISK}"
rm -rf "${DISK}"
