INSTANCE_ID=`(ctx instance id)`

ctx logger info "Will be copied ${DISK}"
qemu-img create -f qcow2 -o backing_file=${DISK} ${INSTANCE_ID}.qcow2

ctx logger info "Copy of image ${INSTANCE_ID}.qcow2"
ctx instance runtime-properties vm_image "`pwd`/${INSTANCE_ID}.qcow2"

ctx logger info "Create cloudinit image"
mkdir -p "${INSTANCE_ID}_cloud"
cd "${INSTANCE_ID}_cloud"
{ echo instance-id: iid-local01; echo local-hostname: ${INSTANCE_ID}; } > meta-data

/bin/cat << EOB > user-data
#cloud-config
password: passw0rd
chpasswd: { expire: False }
ssh_pwauth: True
sudo: ALL=(ALL) NOPASSWD:ALL
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC50fulmwIfQ2EViqi5qmfCrF8qTxcZTYp4YCwFGi9GptJf8dQK/qiFOjMoL4vo++QfIK4CWWlEc3HyukS8LorVP45syhll7SQ55dG5xGaEGTtCknVep76LjRPWWZIwGEgDmY/Iu8h1Hf00M3bzwOcNfkQ+tPX7hJIfjvMgdKz8eL7ZFzjtnTt02J/uouVpiBTOO6Cb8mIsTnY/Z7HmMJB34h3Fwn+xAVEQY+TDAUJch65XMXD+KUzC52nl5qf+gShYBW1UdmNGCQ41h1u508LHhr+gYSofsk0bRfY5hHuA69qL8MClOjTD2ETowSfdwvOzHgqEJv5ls+gmoQhE8RBwiFP1vbR6XM1NF3FoMe7GnaJAO9grvlYq+XkeBY7JkhiHWosVl9QHRE0gO9e8QYxZH1uT+R5Bmt4oLS1bwQLpxQ4N0GnhRfaDWyhh/KNG/CwoThPwOFzOvm2rCcajiqfgJuU5HVSIfU+Ct4C0J7NYZwzrkZgIcYPTot/69hwiPDQ75Jwowi/19ema0zTHQZUc5fZe+UgK/7lHMllPUbmpkmueSdCQc+fNswtk0k/OCFqFzzU5C20ZB7un44Ledz2HROjozFwNi8uVRBhHrL4ie0FjbuE3i9LybPt9x36vDRNo8H2UDaHDOLF3zSaZjkrseKBKFDaZwCFnxpx5m4ZSaQ== cluster@cloudify.co

EOB

genisoimage  -output ../${INSTANCE_ID}-seed.iso -volid cidata -joliet -rock user-data meta-data
qemu-img convert -f raw -O qcow2 ../${INSTANCE_ID}-seed.iso ../${INSTANCE_ID}-seed.qcow2
rm ../${INSTANCE_ID}-seed.iso
cd ..
ctx instance runtime-properties vm_cloudinit "`pwd`/${INSTANCE_ID}-seed.qcow2"
rm -rf "${INSTANCE_ID}_cloud"
