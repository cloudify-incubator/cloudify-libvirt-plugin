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
import time
import uuid

from jinja2 import Template
from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
from pkg_resources import resource_filename
import cloudify_libvirt.common as common


@operation
def create(**kwargs):
    ctx.logger.info("create")
    common.get_libvirt_params(**kwargs)
    # dont need to run anything, we attach disc's in preconfigure state
    # so we will define domain later


@operation
def configure(**kwargs):
    ctx.logger.info("configure")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    domain_file = kwargs.get('domain_file')
    domain_template = kwargs.get('domain_template')

    if domain_file:
        domain_template = ctx.get_resource(domain_file)

    if not domain_file and not domain_template:
        resource_dir = resource_filename(__name__, 'templates')
        domain_file = '{}/domain.xml'.format(resource_dir)
        ctx.logger.info("Will be used internal: %s" % domain_file)

    if not domain_template:
        domain_desc = open(domain_file)
        with domain_desc:
            domain_template = domain_desc.read()

    template_engine = Template(domain_template)
    if not template_params:
        template_params = {}

    if not template_params.get("resource_id"):
        template_params["resource_id"] = ctx.instance.id
    if (not template_params.get("memory_minsize") and
            template_params.get('memory_size')):
        # if have no minimal memory size, set current as minimum
        # and twised memory as maximum
        memory_size = int(template_params['memory_size'])
        template_params["memory_minsize"] = memory_size
        template_params['memory_size'] = memory_size * 2
    if not template_params.get("instance_uuid"):
        template_params["instance_uuid"] = str(uuid.uuid4())
    if not template_params.get("domain_type"):
        template_params["domain_type"] = "qemu"

    params = {"ctx": ctx}
    params.update(template_params)
    xmlconfig = template_engine.render(params)

    ctx.logger.debug(repr(xmlconfig))

    try:
        dom = conn.defineXML(xmlconfig)
        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to define a domain from an XML definition.'
            )

        ctx.instance.runtime_properties['resource_id'] = dom.name()
        ctx.instance.runtime_properties['params'] = template_params
    finally:
        conn.close()


@operation
def start(**kwargs):
    ctx.logger.info("start")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for start")
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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, _ = dom.state()

        for i in xrange(10):
            if state == libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as running.")
                return

            ctx.logger.info("Tring to start vm {}/10".format(i))
            if dom.create() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not start guest domain.'
                )
            time.sleep(30)
            state, _ = dom.state()
    finally:
        conn.close()


@operation
def stop(**kwargs):
    ctx.logger.info("stop")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, _ = dom.state()
        for i in xrange(10):
            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info("Tring to stop vm {}/10".format(i))
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
        ctx.logger.info("No servers for resume")
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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, _ = dom.state()
        for i in xrange(10):
            if state == libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as running.")
                return

            ctx.logger.info("Tring to resume vm {}/10".format(i))
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
        ctx.logger.info("No servers for suspend")
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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, _ = dom.state()
        for i in xrange(10):
            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info("Tring to suspend vm {}/10".format(i))
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

    for _ in xrange(snapshots_count):
        for snapshot in snapshots:
            # we can delete only snapshot without child
            if not snapshot.numChildren():
                ctx.logger.info("Remove {} snapshot."
                                .format(snapshot.getName()))
                snapshot.delete()
        snapshots = dom.listAllSnapshots()

    if len(snapshots):
        subsnapshots = [
            snap.getName() for snap in snapshots
        ]
        raise cfy_exc.RecoverableError(
            "Still have several snapshots: {subsnapshots}."
            .format(subsnapshots=repr(subsnapshots)))


@operation
def delete(**kwargs):
    ctx.logger.info("delete")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        if dom.snapshotNum():
            ctx.logger.info("Domain has {} snapshots."
                            .format(dom.snapshotNum()))
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
            ctx.logger.info("Non critical error: {}".format(str(e)))
            if dom.undefine() < 0:
                raise cfy_exc.RecoverableError(
                    'Can not undefine guest domain.'
                )
        ctx.instance.runtime_properties['resource_id'] = None
    finally:
        conn.close()


@operation
def snapshot_create(**kwargs):
    ctx.logger.info("backup")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for backup.")
        return

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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        if kwargs.get("snapshot_incremental"):
            backup_file = kwargs.get('backup_file')
            backup_template = kwargs.get('backup_template')
            snapshot_type = kwargs.get('snapshot_type')

            if backup_file:
                backup_template = ctx.get_resource(backup_file)

            if not backup_file and not backup_template:
                resource_dir = resource_filename(__name__, 'templates')
                backup_file = '{}/snapshot.xml'.format(resource_dir)
                ctx.logger.info("Will be used internal: %s" % backup_file)

            if not backup_template:
                domain_desc = open(backup_file)
                with domain_desc:
                    backup_template = domain_desc.read()

            template_engine = Template(backup_template)
            if not template_params:
                template_params = {}

            params = {
                "ctx": ctx,
                'snapshot_name': snapshot_name,
                'snapshot_description': snapshot_type
            }
            params.update(template_params)
            xmlconfig = template_engine.render(params)

            ctx.logger.debug(repr(xmlconfig))

            try:
                # will raise exception if unexist
                snapshot = dom.snapshotLookupByName(snapshot_name)
                raise cfy_exc.NonRecoverableError(
                    "Snapshot {snapshot_name} already exists."
                    .format(snapshot_name=snapshot.getName(),))
            except libvirt.libvirtError:
                pass
            snapshot = dom.snapshotCreateXML(xmlconfig)
            ctx.logger.info("Snapshot name: {}".format(snapshot.getName()))
        else:
            if common.read_node_state(common.get_backupdir(kwargs),
                                      resource_id):
                raise cfy_exc.NonRecoverableError(
                    "Backup {snapshot_name} already exists."
                    .format(snapshot_name=snapshot_name,))
            common.save_node_state(common.get_backupdir(kwargs), resource_id,
                                   dom.XMLDesc())
            ctx.logger.info("Backup {snapshot_name} is created."
                            .format(snapshot_name=snapshot_name,))
    finally:
        conn.close()


@operation
def snapshot_delete(**kwargs):
    ctx.logger.info("remove_backup")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for remove_backup.")
        return

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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
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
            if not common.read_node_state(common.get_backupdir(kwargs),
                                          resource_id):
                raise cfy_exc.NonRecoverableError(
                    "No backups found with name: {snapshot_name}."
                    .format(snapshot_name=snapshot_name,))
            common.delete_node_state(common.get_backupdir(kwargs), resource_id)
        ctx.logger.info("Backup deleted: {}".format(snapshot_name))
    finally:
        conn.close()


@operation
def snapshot_apply(**kwargs):
    ctx.logger.info("restore")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for restore.")
        return

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
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        if kwargs.get("snapshot_incremental"):
            # raised exception if libvirt has not found any
            snapshot = dom.snapshotLookupByName(snapshot_name)
            dom.revertToSnapshot(snapshot)
            ctx.logger.info("Reverted to: {}".format(snapshot.getName()))
        else:
            dom_backup = common.read_node_state(common.get_backupdir(kwargs),
                                                resource_id)
            if not dom_backup:
                raise cfy_exc.NonRecoverableError(
                    "No backups found with name: {snapshot_name}."
                    .format(snapshot_name=snapshot_name,))

            if dom_backup.strip() != dom.XMLDesc().strip():
                ctx.logger.info("We have different configs,\n{}\nvs\n{}\n"
                                .format(
                                    repr(dom_backup.strip()),
                                    repr(dom.XMLDesc().strip())))
            else:
                ctx.logger.info("Already used such configuration: {}"
                                .format(snapshot_name))
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
        ctx.logger.info("No servers for statistics.")
        return

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        statistics = ctx.instance.runtime_properties.get('stat', {})

        before_usage = _current_use(dom)

        # usage generated by compare cpu_time before
        # and after sleep for 5 seconds.
        ctx.logger.debug("Used: {} seconds.".format(before_usage))
        time.sleep(5)
        statistics['cpu'] = 100 * (_current_use(dom) - before_usage) / 5

        memory = dom.memoryStats()
        statistics['memory'] = memory.get('actual', 0) / 1024.0
        ctx.instance.runtime_properties['stat'] = statistics

        ctx.logger.info("Statistics: {}".format(repr(statistics)))
    finally:
        conn.close()
