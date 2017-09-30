DISK=`ctx instance runtime-properties bios_flash`
ctx logger info "Will be deleted ${DISK}"
rm -rf "${DISK}"
