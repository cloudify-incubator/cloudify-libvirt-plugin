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
import time
from lxml import etree

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import utils


@operation
def create(**kwargs):
    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    server = {
        'name': ctx.instance.id,
    }
    server.update(ctx.node.properties.get('server', {}))
    server.update(kwargs.get('server', {}))

    xmlns = ctx.node.properties.get('metadata', {}).get('xmlns', {})

    for name in kwargs['payload']:
        node = utils.generate_xml_node(
            kwargs['payload'][name],
            xmlns,
            name
        )

        xmlconfig = etree.tostring(
            node, pretty_print=True, xml_declaration=True,
            encoding='UTF-8'
        )

        ctx.logger.info(xmlconfig)

        dom = conn.defineXML(xmlconfig)
        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to define a domain from an XML definition.'
            )

        ctx.instance.runtime_properties['resource_id'] = dom.name()

        if dom.create() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not boot guest domain.'
            )

        ctx.logger.info('Guest ' + dom.name() + ' has booted')
        ctx.instance.runtime_properties['resource_id'] = dom.name()
        conn.close()


@operation
def configure(**kwargs):
    ctx.logger.info("configure")


@operation
def start(**kwargs):
    ctx.logger.info("start")


@operation
def stop(**kwargs):

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
        return

    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    dom = conn.lookupByName(resource_id)
    if dom is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to find the domain'
        )

    for i in xrange(10):
        ctx.logger.info("Tring to stop vm")
        if dom.shutdown() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not shutdown guest domain.'
            )
        time.sleep(30)

        state, reason = dom.state()

        if state == libvirt.VIR_DOMAIN_SHUTOFF:
            ctx.logger.info("Looks as stoped Tring to stop vm")
            return

    conn.close()


@operation
def delete(**kwargs):
    ctx.logger.info("delete")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
        return

    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    dom = conn.lookupByName(resource_id)
    if dom is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to find the domain'
        )

    state, reason = dom.state()

    if state != libvirt.VIR_DOMAIN_SHUTOFF:
        if dom.destroy() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not destroy guest domain.'
            )

    if dom.undefine() < 0:
        raise cfy_exc.NonRecoverableError(
            'Can not undefine guest domain.'
        )

    conn.close()
