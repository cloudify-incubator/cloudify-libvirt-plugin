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
import uuid
import time

from jinja2 import Template
from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
from pkg_resources import resource_filename


@operation
def create(**kwargs):
    ctx.logger.info("create")

    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    network_file = kwargs.get('network_file')
    network_template = kwargs.get('network_template')

    template_params = ctx.node.properties.get('params', {})
    template_params.update(ctx.instance.runtime_properties.get('params', {}))
    template_params.update(kwargs.get('params', {}))

    if not network_file and not network_template:
        resource_dir = resource_filename(__name__, 'templates')
        network_file = '{}/network.xml'.format(resource_dir)
        ctx.logger.info("Will be used internal: %s" % network_file)

    if not network_template:
        domain_desc = open(network_file)
        with domain_desc:
            network_template = domain_desc.read()

    template_engine = Template(network_template)
    if not template_params:
        template_params = {}

    if not template_params.get("resource_id"):
        template_params["resource_id"] = ctx.instance.id
    if not template_params.get("instance_uuid"):
        template_params["instance_uuid"] = str(uuid.uuid4())

    # supply ctx for template for reuse runtime params
    template_params['ctx'] = ctx
    xmlconfig = template_engine.render(template_params)

    ctx.logger.info(xmlconfig)

    # create a persistent virtual network
    network = conn.networkCreateXML(xmlconfig)
    if network is None:
        raise cfy_exc.NonRecoverableError('Failed to create a virtual network')
    active = network.isActive()
    if active == 1:
        ctx.logger.info('The new persistent virtual network is active')
    else:
        ctx.logger.info('The new persistent virtual network is not active')

    ctx.logger.info('Network ' + network.name() + ' has created.')
    ctx.instance.runtime_properties['resource_id'] = network.name()
    del template_params['ctx']
    ctx.logger.info('Params: ' + repr(template_params))
    ctx.instance.runtime_properties['params'] = template_params
    conn.close()

@operation
def delete(**kwargs):
    ctx.logger.info("delete")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No network for delete")
        return

    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    # lookup the default network by name
    network = conn.networkLookupByName(resource_id)
    if network is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to find the network'
        )

    if network.destroy() < 0:
        raise cfy_exc.NonRecoverableError(
            'Can not undefine network.'
        )

    conn.close()


@operation
def link(**kwargs):
    ctx.logger.info("link")
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    resource_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Network: ' + repr(resource_id) + ' to VM: ' + repr(vm_id) + ' .')

    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    # lookup the default network by name
    network = conn.networkLookupByName(resource_id)
    if network is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to find the network'
        )

    for i in xrange(10):
        ctx.logger.info("Tring to get vm ip")
        for lease in network.DHCPLeases():
            vm_params = ctx.source.instance.runtime_properties.get(
                'params', {})
            for network in vm_params.get("networks", []):
                if network.get('mac') == lease.get('mac'):
                    ctx.source.instance.runtime_properties['ip'] = lease.get(
                        'ipaddr')
                    ctx.logger.info("Found: " + lease.get('ipaddr'))
                    return
            else:
                # we don't have networks in vm?
                return
        time.sleep(30)

    raise cfy_exc.NonRecoverableError(
        'No ip for now, try later'
    )


@operation
def unlink(**kwargs):
    ctx.logger.info("unlink")
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    network_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Network: ' + repr(network_id) + ' to VM: ' + repr(vm_id) + ' .')
    ctx.target.instance.runtime_properties['ip'] = None
