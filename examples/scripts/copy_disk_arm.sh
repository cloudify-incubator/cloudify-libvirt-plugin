INSTANCE_ID=`(ctx instance id)`

ctx logger info "Flash will be copied"

dd if=/dev/zero of=${INSTANCE_ID}-flash.img bs=1M count=64
ctx instance runtime-properties bios_flash "`pwd`/${INSTANCE_ID}-flash.img"
