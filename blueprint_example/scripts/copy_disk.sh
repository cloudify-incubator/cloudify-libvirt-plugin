ctx logger info "Will be copied ${DISK}"

INSTANCE_ID=`(ctx instance id)`

qemu-img create -f qcow2 -o backing_file=${DISK} ${INSTANCE_ID}.qcow2

ctx logger info "Copy of image ${INSTANCE_ID}.qcow2"

ctx instance runtime-properties vm_image "`pwd`/${INSTANCE_ID}.qcow2"
