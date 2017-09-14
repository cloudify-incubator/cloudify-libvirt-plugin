LANG=C wget -cv wget https://people.debian.org/~aurel32/qemu/amd64/debian_wheezy_amd64_standard.qcow2

ctx instance runtime-properties vm_image "`pwd`/debian_wheezy_amd64_standard.qcow2"
