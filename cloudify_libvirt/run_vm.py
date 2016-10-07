import libvirt
import sys
import time


if dom.shutdown() < 0:
    print 'Can not shutdown guest domain.'

time.sleep(10)

state, reason = dom.state()

if state != libvirt.VIR_DOMAIN_SHUTOFF:
    if dom.destroy() < 0:
        print 'Can not destroy guest domain.'
        exit(1)

if dom.undefine() < 0:
    print 'Can not undefine guest domain.'
    exit(1)

conn.close()
exit(0)
