# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
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

from builtins import str

import libvirt
import time

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import cloudify_libvirt.common as common


@operation
def create(**kwargs):
    ctx.logger.info("create")
    common.get_libvirt_params(**kwargs)
    # dont need to run anything, we attach disc's in preconfigure state
    # so we will define domain later


def _update_template_params(template_params):
    # set all params to default values
    if (not template_params.get("memory_maxsize") and
            template_params.get('memory_size')):
        # if have no maximum memory size, set current as minimum
        # and twised memory as maximum
        memory_size = int(template_params['memory_size'])
        template_params['memory_maxsize'] = memory_size * 2
    if not template_params.get("domain_type"):
        template_params["domain_type"] = "qemu"
    if not template_params.get("domain_cpu"):
        template_params["domain_cpu"] = "custom"


@operation
def configure(**kwargs):
    ctx.logger.info("configure")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    _update_template_params(template_params)
    try:
        if ctx.instance.runtime_properties.get("use_external_resource"):
            # lookup the default domain by name
            resource_id = ctx.instance.runtime_properties["resource_id"]
            try:
                dom = conn.lookupByName(resource_id)
            except libvirt.libvirtError as e:
                raise cfy_exc.NonRecoverableError(
                    f'Failed to find the domain: {repr(e)}'
                )

            # save settings
            ctx.instance.runtime_properties['params'] = template_params
            ctx.instance.runtime_properties['resource_id'] = dom.name()
            ctx.instance.runtime_properties['use_external_resource'] = True
            return

        resource_id = ctx.instance.runtime_properties.get('resource_id')
        if resource_id:
            ctx.logger.info("Domain is already alive, skip create.")
            try:
                dom = conn.lookupByName(resource_id)
            except libvirt.libvirtError as e:
                raise cfy_exc.NonRecoverableError(
                    f'Failed to find the domain: {repr(e)}'
                )
        else:
            xmlconfig = common.gen_xml_template(
                kwargs, template_params, 'domain')
            dom = conn.defineXML(xmlconfig)
            if dom is None:
                raise cfy_exc.NonRecoverableError(
                    'Failed to define a domain from an XML definition.'
                )

            ctx.instance.runtime_properties['resource_id'] = dom.name()
            ctx.instance.runtime_properties['params'] = template_params
    finally:
        conn.close()


def _update_network_list(dom, lease_only=True):
    if lease_only:
        request_type = libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
    else:
        request_type = libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT

    # get known by libvirt interfaces
    virt_networks = dom.interfaceAddresses(request_type)
    ctx.logger.info(f"Libvirt knows about such networks: {repr(virt_networks)}")

    # networks from instance
    if 'params' not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties['params'] = {}
    # add networks
    if 'networks' not in ctx.instance.runtime_properties['params']:
        ctx.instance.runtime_properties['params']['networks'] = []
    # instance networks
    instance_networks = ctx.instance.runtime_properties['params']["networks"]

    for virt_name in virt_networks:
        lease = virt_networks[virt_name]
        for vm_network in instance_networks:
            # copy current state
            if vm_network.get('mac') == lease.get('hwaddr'):
                vm_network['dev'] = virt_name
                vm_network['addrs'] = lease.get('addrs', [])
                # force update
                ctx.instance.runtime_properties._set_changed()
                break
        else:
            if lease.get('hwaddr'):
                instance_networks.append({
                    'dev': virt_name,
                    'addrs': lease.get('addrs', []),
                    'mac': lease['hwaddr']
                })
                # force update
                ctx.instance.runtime_properties._set_changed()

    if ctx.instance.runtime_properties.get('ip'):
        # we already have some ip
        return

    for vm_network in instance_networks:
        for ip_addr in vm_network.get('addrs', []):
            if ip_addr.get('type') == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                ctx.instance.runtime_properties['ip'] = ip_addr['addr']
                return


@operation
def reboot(**kwargs):
    ctx.logger.info("reboot")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for reboot")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        if dom.reboot() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not reboot guest domain.'
            )
    finally:
        conn.close()


@operation
def update(**kwargs):
    ctx.logger.info("set vcpu/memory values")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for update")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        # change memory values
        if template_params.get('memory_size'):
            ctx.logger.info(f"Set memory to {repr(template_params['memory_size'])}")
            if dom.setMemory(template_params['memory_size']) < 0:
                raise cfy_exc.NonRecoverableError(
                    "Can not change memory amount."
                )

        state, _ = dom.state()
        if state == libvirt.VIR_DOMAIN_RUNNING:
            ctx.logger.info("CPU/Maximum memory size count should be changed "
                            "on stopped vm.")
            return

        # change vcpu values
        if template_params.get('vcpu'):
            ctx.logger.info(f"Set cpu count to {repr(template_params['vcpu'])}")
            if dom.setVcpus(template_params['vcpu']) < 0:
                raise cfy_exc.NonRecoverableError(
                    "Can not change cpu count."
                )

        # change max memory values
        if template_params.get('memory_maxsize'):
            ctx.logger.info("Set max memory to {}"
                            .format(repr(template_params['memory_maxsize'])))
            if dom.setMaxMemory(template_params['memory_maxsize']) < 0:
                raise cfy_exc.NonRecoverableError(
                    "Can not change max memory amount."
                )

    finally:
        conn.close()


@operation
def start(**kwargs):
    ctx.logger.info("start")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for start")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    # wait for ip on start
    wait_for_ip = template_params.get('wait_for_ip', False)

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        for i in range(10):
            state, _ = dom.state()
            ctx.logger.info(f"Trying to start vm {i}/10")
            if wait_for_ip:
                ctx.logger.info("Waiting for ip.")
            if state == libvirt.VIR_DOMAIN_RUNNING:
                _update_network_list(dom)
                # wait for ip check
                if not wait_for_ip or (
                    wait_for_ip and ctx.instance.runtime_properties.get('ip')
                ):
                    ctx.logger.info("Looks as running.")
                    return
            elif dom.create() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not start guest domain.'
                )

            time.sleep(30)

        # still no ip
        if wait_for_ip:
            raise cfy_exc.RecoverableError(
                'No ip for now, try later'
            )
    finally:
        conn.close()


@operation
def stop(**kwargs):
    ctx.logger.info("stop")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No servers for stop")
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
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        # reset ip on stop
        ctx.instance.runtime_properties['ip'] = None

        state, _ = dom.state()
        for i in range(10):
            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info(f"Trying to stop vm {i}/10")
            if dom.shutdown() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not shutdown guest domain.'
                )
            time.sleep(30)
            state, _ = dom.state()
    finally:
        conn.close()


@operation
def resume(**kwargs):
    ctx.logger.info("resume")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for resume")

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        state, _ = dom.state()
        for i in range(10):
            if state == libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as running.")
                return

            ctx.logger.info(f"Trying to resume vm {i}/10")
            if dom.resume() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not suspend guest domain.'
                )
            time.sleep(30)
            state, _ = dom.state()
    finally:
        conn.close()


@operation
def suspend(**kwargs):
    ctx.logger.info("suspend")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for suspend")

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        state, _ = dom.state()
        for i in range(10):
            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info(f"Trying to suspend vm {i}/10")
            if dom.suspend() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not suspend guest domain.'
                )
            time.sleep(30)
            state, _ = dom.state()
    finally:
        conn.close()


def _cleanup_snapshots(ctx, dom):
    snapshots = dom.listAllSnapshots()
    snapshots_count = len(snapshots)

    for _ in range(snapshots_count):
        for snapshot in snapshots:
            # we can delete only snapshot without child
            if not snapshot.numChildren():
                ctx.logger.info(f"Remove {snapshot.getName()} snapshot.")
                snapshot.delete()
        snapshots = dom.listAllSnapshots()

    if len(snapshots):
        subsnapshots = [
            snap.getName() for snap in snapshots
        ]
        raise cfy_exc.RecoverableError(
            f"Still have several snapshots: {repr(subsnapshots)}."
            )


def _delete_force(dom):
    """remove domain internaly without cleanup for properties"""
    if dom.snapshotNum():
        ctx.logger.info(f"Domain has {dom.snapshotNum()} snapshots.")
        _cleanup_snapshots(ctx, dom)

    state, _ = dom.state()

    if state != libvirt.VIR_DOMAIN_SHUTOFF:
        if dom.destroy() < 0:
            raise cfy_exc.RecoverableError(
                'Can not destroy guest domain.'
            )

    try:
        if dom.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_NVRAM) < 0:
            raise cfy_exc.RecoverableError(
                'Can not undefine guest domain with NVRAM.'
            )
    except AttributeError as e:
        ctx.logger.info(f"Non critical error: {str(e)}")
        if dom.undefine() < 0:
            raise cfy_exc.RecoverableError(
                'Can not undefine guest domain.'
            )


@operation
def delete(**kwargs):
    ctx.logger.info("delete")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No servers for delete")
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
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        _delete_force(dom)
        ctx.instance.runtime_properties['resource_id'] = None
    finally:
        conn.close()


def _backup_create(conn, dom, resource_id, snapshot_name, full_dump, kwargs):
    if full_dump:
        ctx.logger.info("Used full raw dump")
        # dump domain with memory and recreate domain
        # all snapshots will be removed
        if common.check_binary_place(common.get_backupdir(kwargs),
                                     resource_id):
            raise cfy_exc.NonRecoverableError(f"Backup {snapshot_name} already exists.")
        # create place for store
        common.create_binary_place(common.get_backupdir(kwargs))
        # save backup to directory (domain will be removed)
        dom.save(common.get_binary_place(common.get_backupdir(kwargs),
                                         resource_id))
        # restore from backup
        conn.restore(common.get_binary_place(common.get_backupdir(kwargs),
                                             resource_id))
    else:
        # non-destructive export for domain
        if common.read_node_state(common.get_backupdir(kwargs),
                                  resource_id):
            raise cfy_exc.NonRecoverableError(f"Backup {snapshot_name} already exists.")
        common.save_node_state(common.get_backupdir(kwargs), resource_id,
                               dom.XMLDesc())


@operation
def snapshot_create(**kwargs):
    ctx.logger.info("backup")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for backup.")

    snapshot_name = common.get_backupname(kwargs)

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        if kwargs.get("snapshot_incremental"):
            snapshot_type = kwargs.get('snapshot_type')

            params = {
                'snapshot_name': snapshot_name,
                'snapshot_description': snapshot_type
            }
            if template_params:
                params.update(template_params)
            xmlconfig = common.gen_xml_template(kwargs, params, 'snapshot')

            try:
                # will raise exception if unexist
                snapshot = dom.snapshotLookupByName(snapshot_name)
                raise cfy_exc.NonRecoverableError(
                    f"Snapshot {snapshot.getName()} already exists."
                )
            except libvirt.libvirtError:
                pass
            snapshot = dom.snapshotCreateXML(xmlconfig)
            ctx.logger.info(f"Snapshot name: {snapshot.getName()}")
        else:
            _backup_create(
                conn, dom, resource_id, snapshot_name,
                template_params.get('full_dump', False),
                kwargs)
            ctx.logger.info(f"Backup {snapshot_name} is created.")
    finally:
        conn.close()


def _backup_delete(dom, resource_id, snapshot_name, full_dump, kwargs):
    if full_dump:
        ctx.logger.info("Used full raw dump")
        # remove raw domain state
        if not common.check_binary_place(common.get_backupdir(kwargs),
                                         resource_id):
            raise cfy_exc.NonRecoverableError(
                f"No backups found with name: {snapshot_name}."
                )
        common.delete_binary_place(common.get_backupdir(kwargs),
                                   resource_id)
    else:
        # remove xml dump only
        if not common.read_node_state(common.get_backupdir(kwargs),
                                      resource_id):
            raise cfy_exc.NonRecoverableError(
                f"No backups found with name: {snapshot_name}."
                )
        common.delete_node_state(common.get_backupdir(kwargs), resource_id)


@operation
def snapshot_delete(**kwargs):
    ctx.logger.info("remove_backup")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for remove_backup.")

    snapshot_name = common.get_backupname(kwargs)

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        if kwargs.get("snapshot_incremental"):
            # raised exception if libvirt has not found any
            snapshot = dom.snapshotLookupByName(snapshot_name)
            if snapshot.numChildren():
                subsnapshots = [
                    snap.getName() for snap in snapshot.listAllChildren()
                ]
                raise cfy_exc.NonRecoverableError(
                    "Sub snapshots {subsnapshots} found for {snapshot_name}. "
                    "You should remove subsnaphots before remove current."
                    .format(snapshot_name=snapshot_name,
                            subsnapshots=repr(subsnapshots)))
            snapshot.delete()
        else:
            _backup_delete(
                dom, resource_id, snapshot_name,
                template_params.get('full_dump', False), kwargs)
        ctx.logger.info(f"Backup deleted: {snapshot_name}")
    finally:
        conn.close()


def _backup_apply(conn, dom, resource_id, snapshot_name, full_dump, kwargs):
    if full_dump:
        ctx.logger.info("Used full raw dump")
        # restore domain with memory and recreate domain
        # all snapshots will be removed
        if not common.check_binary_place(common.get_backupdir(kwargs),
                                         resource_id):
            raise cfy_exc.NonRecoverableError(
                f"No backups found with name: {snapshot_name}."
                )

        # old domain will be removed
        _delete_force(dom)
        # and new created
        conn.restore(common.get_binary_place(common.get_backupdir(kwargs),
                                             resource_id))
    else:
        # light version of backup
        dom_backup = common.read_node_state(common.get_backupdir(kwargs),
                                            resource_id)
        if not dom_backup:
            raise cfy_exc.NonRecoverableError(
                f"No backups found with name: {snapshot_name}."
                )

        if dom_backup.strip() != dom.XMLDesc().strip():
            ctx.logger.info("We have different configs,\n{}\nvs\n{}\n"
                            .format(
                                repr(dom_backup.strip()),
                                repr(dom.XMLDesc().strip())))
        else:
            ctx.logger.info(f"Already used such configuration: {snapshot_name}")


@operation
def snapshot_apply(**kwargs):
    ctx.logger.info("restore")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for restore.")

    snapshot_name = common.get_backupname(kwargs)

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        if kwargs.get("snapshot_incremental"):
            # raised exception if libvirt has not found any
            snapshot = dom.snapshotLookupByName(snapshot_name)
            dom.revertToSnapshot(snapshot)
            ctx.logger.info(f"Reverted to: {snapshot.getName()}")
        else:
            _backup_apply(
                conn, dom, resource_id, snapshot_name,
                template_params.get('full_dump', False), kwargs)
            ctx.logger.info(f"Restored to: {snapshot_name}")
    finally:
        conn.close()


def _current_use(dom):
    total_list = dom.getCPUStats(True)
    if len(total_list):
        total = total_list[0]
    else:
        total = {}
    return (
        total.get('user_time', 0) + total.get('system_time', 0) +
        total.get('cpu_time', 0)
    ) / 1000000000.0


@operation
def perfomance(**kwargs):
    ctx.logger.info("update statistics")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No servers for statistics.")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the domain: {repr(e)}'
            )

        statistics = ctx.instance.runtime_properties.get('stat', {})

        before_usage = _current_use(dom)

        # usage generated by compare cpu_time before
        # and after sleep for 5 seconds.
        ctx.logger.debug(f"Used: {before_usage} seconds.")
        time.sleep(5)
        statistics['cpu'] = 100 * (_current_use(dom) - before_usage) // 5

        memory = dom.memoryStats()
        statistics['memory'] = memory.get('actual', 0) / 1024.0
        ctx.instance.runtime_properties['stat'] = statistics

        ctx.logger.info(f"Statistics: {repr(statistics)}")
    finally:
        conn.close()
