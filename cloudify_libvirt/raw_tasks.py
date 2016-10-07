########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import libvirt
import sys
import time

from cloudify import ctx
from cloudify.decorators import operation


@operation
def create(**kwargs):
    conn = libvirt.open('qemu:///system')
    if conn == None:
        print 'Failed to open connection to the hypervisor'
        sys.exit(1)

    xmlconfig="""<domain type='qemu'>
      <name>ubuntu-server</name>
      <uuid>8dcd1143-bafc-dc37-2fbd-27e6a1e3ca5c</uuid>
      <memory unit='KiB'>65536</memory>
      <currentMemory unit='KiB'>65536</currentMemory>
      <vcpu placement='static'>1</vcpu>
      <resource>
        <partition>/machine</partition>
      </resource>
      <os>
        <type arch='x86_64' machine='pc-i440fx-trusty'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
        <pae/>
      </features>
      <clock offset='utc'/>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>restart</on_crash>
      <devices>
        <emulator>/usr/bin/qemu-system-x86_64</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='raw'/>
          <source file='/home/clouduser/Downloads/linux-0.2.img'/>
          <target dev='hda' bus='ide'/>
          <alias name='ide0-0-0'/>
          <address type='drive' controller='0' bus='0' target='0' unit='0'/>
        </disk>
        <controller type='usb' index='0'>
          <alias name='usb0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x2'/>
        </controller>
        <controller type='pci' index='0' model='pci-root'>
          <alias name='pci.0'/>
        </controller>
        <controller type='ide' index='0'>
          <alias name='ide0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
        </controller>
        <interface type='network'>
          <mac address='52:54:00:23:fe:37'/>
          <source network='default'/>
          <target dev='vnet0'/>
          <model type='rtl8139'/>
          <alias name='net0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
        </interface>
        <serial type='pty'>
          <source path='/dev/pts/1'/>
          <target port='0'/>
          <alias name='serial0'/>
        </serial>
        <console type='pty' tty='/dev/pts/1'>
          <source path='/dev/pts/1'/>
          <target type='serial' port='0'/>
          <alias name='serial0'/>
        </console>
        <input type='mouse' bus='ps2'/>
        <input type='keyboard' bus='ps2'/>
        <graphics type='vnc' port='5900' autoport='yes' listen='127.0.0.1'>
          <listen type='address' address='127.0.0.1'/>
        </graphics>
        <video>
          <model type='cirrus' vram='9216' heads='1'/>
          <alias name='video0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
        </video>
        <memballoon model='virtio'>
          <alias name='balloon0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
        </memballoon>
      </devices>
      <seclabel type='dynamic' model='apparmor' relabel='yes'>
        <label>libvirt-8dcd1143-bafc-dc37-2fbd-27e6a1e3ca5c</label>
        <imagelabel>libvirt-8dcd1143-bafc-dc37-2fbd-27e6a1e3ca5c</imagelabel>
      </seclabel>
    </domain>"""

    dom = conn.defineXML(xmlconfig)
    if dom == None:
        print 'Failed to define a domain from an XML definition.'
        exit(1)

    if dom.create() < 0:
        print 'Can not boot guest domain.'
        exit(1)

    print 'Guest '+dom.name()+' has booted'

    ctx.logger.info("create")


@operation
def configure(**kwargs):
    ctx.logger.info("configure")


@operation
def start(**kwargs):
    ctx.logger.info("start")


@operation
def stop(**kwargs):
    conn = libvirt.open('qemu:///system')
    if conn == None:
        print 'Failed to open connection to the hypervisor'
        sys.exit(1)

    dom = conn.lookupByName('ubuntu-server')
    if dom == None:
        print 'Failed to find the domain'
        exit(1)


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
    ctx.logger.info("stop")


@operation
def delete(**kwargs):
    ctx.logger.info("delete")
