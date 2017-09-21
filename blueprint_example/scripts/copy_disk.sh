INSTANCE_ID=`(ctx instance id)`

ctx logger info "Will be copied ${DISK}"
qemu-img create -f qcow2 -o backing_file=${DISK} ${INSTANCE_ID}.qcow2

ctx logger info "Copy of image ${INSTANCE_ID}.qcow2"
ctx instance runtime-properties vm_image "`pwd`/${INSTANCE_ID}.qcow2"

ctx logger info "Create cloudinit image"
mkdir -p "${INSTANCE_ID}_cloud"
cd "${INSTANCE_ID}_cloud"
{ echo instance-id: iid-local01; echo local-hostname: ${INSTANCE_ID}; } > meta-data
printf "#cloud-config\npassword: passw0rd\nchpasswd: { expire: False }\nssh_pwauth: True\n" > user-data
genisoimage  -output ../${INSTANCE_ID}-seed.iso -volid cidata -joliet -rock user-data meta-data
cd ..
ctx instance runtime-properties vm_cloudinit "`pwd`/${INSTANCE_ID}-seed.iso"
rm -rf "${INSTANCE_ID}_cloud"
