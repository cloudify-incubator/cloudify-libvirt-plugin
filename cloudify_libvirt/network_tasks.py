########
# Copyright (c) 2016-2018 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import libvirt
import uuid
import time

from jinja2 import Template
from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
from pkg_resources import resource_filename
from cloudify_libvirt.common import get_libvirt_params


@operation
def create(**kwargs):
    ctx.logger.info("Creating new network.")

    libvirt_auth, template_params = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        network_file = kwargs.get('network_file')
        network_template = kwargs.get('network_template')

        if network_file:
            network_template = ctx.get_resource(network_file)

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

        params = {"ctx": ctx}
        params.update(template_params)
        xmlconfig = template_engine.render(params)

        ctx.logger.debug(repr(xmlconfig))

        # create a persistent virtual network
        network = conn.networkCreateXML(xmlconfig)
        if network is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to create a virtual network')

        ctx.logger.info('Network ' + network.name() + ' has created.')
        ctx.logger.info('Params: ' + repr(template_params))
        ctx.instance.runtime_properties['params'] = template_params
        ctx.instance.runtime_properties['resource_id'] = network.name()

        active = network.isActive()
        if active == 1:
            ctx.logger.info('The new persistent virtual network is active')
        else:
            ctx.logger.info('The new persistent virtual network is not active')
    finally:
        conn.close()


@operation
def delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Delete: {}".format(repr(resource_id)))

    if not resource_id:
        ctx.logger.info("No network for delete")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
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

        ctx.instance.runtime_properties['resource_id'] = None
    finally:
        conn.close()


@operation
def link(**kwargs):
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    net_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Link network: {} to VM: {}.'
                    .format(repr(net_id), repr(vm_id)))

    libvirt_auth = ctx.target.instance.runtime_properties.get('libvirt_auth')
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default network by name
        network = conn.networkLookupByName(net_id)
        if network is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the network'
            )

        MAX_RETRY = 10
        for i in xrange(MAX_RETRY):
            ctx.logger.info("{}: Tring to get vm ip: {}/{}"
                            .format(vm_id, i, MAX_RETRY))
            for lease in network.DHCPLeases():
                source_properties = ctx.source.instance.runtime_properties
                vm_params = source_properties.get(
                    'params', {})
                for vm_network in vm_params.get("networks", []):
                    if vm_network.get('mac') == lease.get('mac'):
                        source_properties['ip'] = lease.get('ipaddr')
                        ctx.logger.info("{}:Found: {}"
                                        .format(vm_id, lease.get('ipaddr')))
                        return
            # we have never get ip before 60 sec, so wait 60 as minimum
            time.sleep(60)

        raise cfy_exc.RecoverableError(
            'No ip for now, try later'
        )
    finally:
        conn.close()


@operation
def unlink(**kwargs):
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    net_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Unlink network: {} to VM: {}.'
                    .format(repr(net_id), repr(vm_id)))

    ctx.target.instance.runtime_properties['ip'] = None
