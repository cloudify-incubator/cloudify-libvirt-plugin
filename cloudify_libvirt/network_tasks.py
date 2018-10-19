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

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import cloudify_libvirt.common as common


def _update_template_params(template_params):
    # set all params to default values
    if not template_params:
        template_params = {}

    if not template_params:
        template_params = {}

    if not template_params.get("resource_id"):
        template_params["resource_id"] = ctx.instance.id
    if not template_params.get("instance_uuid"):
        template_params["instance_uuid"] = str(uuid.uuid4())
    return template_params


@operation
def create(**kwargs):
    ctx.logger.info("Creating new network.")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    template_params = _update_template_params(template_params)

    try:
        if ctx.instance.runtime_properties.get("use_external_resource"):
            # lookup the default network by name
            resource_id = ctx.instance.runtime_properties["resource_id"]
            try:
                network = conn.networkLookupByName(resource_id)
            except libvirt.libvirtError as e:
                raise cfy_exc.NonRecoverableError(
                    'Failed to find the network: {}'.format(repr(e))
                )

            # save settings
            ctx.instance.runtime_properties['params'] = template_params
            ctx.instance.runtime_properties['resource_id'] = network.name()
            ctx.instance.runtime_properties['use_external_resource'] = True
            return

        xmlconfig = common.gen_xml_template(kwargs, template_params, 'network')

        # create a persistent virtual network
        network = conn.networkCreateXML(xmlconfig)
        if network is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to create a virtual network')

        ctx.logger.info('Network ' + network.name() + ' has created.')
        ctx.logger.info('Params: ' + repr(template_params))
        ctx.instance.runtime_properties['params'] = template_params
        ctx.instance.runtime_properties['resource_id'] = network.name()
        ctx.instance.runtime_properties['use_external_resource'] = False

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
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No network for delete")
        return

    if ctx.instance.runtime_properties.get('use_external_resource'):
        ctx.logger.info("External resource, skip")
        return

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default network by name
        try:
            network = conn.networkLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the network: {}'.format(repr(e))
            )

        if network.destroy() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not undefine network.'
            )

        ctx.instance.runtime_properties['resource_id'] = None
        ctx.instance.runtime_properties['backups'] = {}
    finally:
        conn.close()


@operation
def snapshot_create(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot create: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No network for backup")

    snapshot_name = common.get_backupname(kwargs)
    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default network by name
        try:
            network = conn.networkLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the network: {}'.format(repr(e))
            )

        net_backup = network.XMLDesc()
        if kwargs.get("snapshot_incremental"):
            backups = ctx.instance.runtime_properties.get("backups", {})
            if snapshot_name in backups:
                raise cfy_exc.NonRecoverableError(
                    "Snapshot {snapshot_name} already exists."
                    .format(snapshot_name=snapshot_name,))
            backups[snapshot_name] = net_backup
            ctx.instance.runtime_properties["backups"] = backups
            ctx.logger.info("Snapshot {snapshot_name} is created."
                            .format(snapshot_name=snapshot_name,))
        else:
            if common.read_node_state(common.get_backupdir(kwargs),
                                      resource_id):
                raise cfy_exc.NonRecoverableError(
                    "Backup {snapshot_name} already exists."
                    .format(snapshot_name=snapshot_name,))
            common.save_node_state(common.get_backupdir(kwargs), resource_id,
                                   net_backup)
        ctx.logger.info("Backup {snapshot_name} is created."
                        .format(snapshot_name=snapshot_name,))
        ctx.logger.debug("Current config {}".format(repr(net_backup)))
    finally:
        conn.close()


@operation
def snapshot_apply(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot restore for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No network for restore")

    snapshot_name = common.get_backupname(kwargs)

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default network by name
        try:
            network = conn.networkLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the network: {}'.format(repr(e))
            )

        if kwargs.get("snapshot_incremental"):
            backups = ctx.instance.runtime_properties.get("backups", {})
            if snapshot_name not in backups:
                raise cfy_exc.NonRecoverableError(
                    "No snapshots found with name: {snapshot_name}."
                    .format(snapshot_name=snapshot_name,))
            net_backup = backups[snapshot_name]
        else:
            net_backup = common.read_node_state(common.get_backupdir(kwargs),
                                                resource_id)
            if not net_backup:
                raise cfy_exc.NonRecoverableError(
                    "No backups found with name: {snapshot_name}."
                    .format(snapshot_name=snapshot_name,))

        if net_backup.strip() != network.XMLDesc().strip():
            ctx.logger.info("We have different configs,\n{}\nvs\n{}\n"
                            .format(
                                repr(net_backup.strip()),
                                repr(network.XMLDesc().strip())))
        else:
            ctx.logger.info("Already used such configuration: {}"
                            .format(snapshot_name))
    finally:
        conn.close()


@operation
def snapshot_delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot delete for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No network for backup delete")

    snapshot_name = common.get_backupname(kwargs)
    if kwargs.get("snapshot_incremental"):
        backups = ctx.instance.runtime_properties.get("backups", {})
        if snapshot_name not in backups:
            raise cfy_exc.NonRecoverableError(
                "No snapshots found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))
        del backups[snapshot_name]
        ctx.instance.runtime_properties["backups"] = backups
    else:
        if not common.read_node_state(common.get_backupdir(kwargs),
                                      resource_id):
            raise cfy_exc.NonRecoverableError(
                "No backups found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))
        common.delete_node_state(common.get_backupdir(kwargs), resource_id)
    ctx.logger.info("Backup deleted: {}".format(snapshot_name))


@operation
def link(**kwargs):
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    resource_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Link network: {} to VM: {}.'
                    .format(repr(resource_id), repr(vm_id)))

    libvirt_auth = ctx.target.instance.runtime_properties.get('libvirt_auth')
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default network by name
        try:
            network = conn.networkLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the network: {}'.format(repr(e))
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
    resource_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Unlink network: {} to VM: {}.'
                    .format(repr(resource_id), repr(vm_id)))

    ctx.target.instance.runtime_properties['ip'] = None
