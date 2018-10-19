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

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import cloudify_libvirt.common as common


def _update_template_params(template_params):
    # set all params to default values
    if not template_params.get("path"):
        template_params["path"] = (
            "/var/lib/libvirt/images/{}".format(template_params["name"]))


@operation
def create(**kwargs):
    ctx.logger.info("Creating new pool.")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    _update_template_params(template_params)
    try:
        if ctx.instance.runtime_properties.get("use_external_resource"):
            # lookup the default pool by name
            resource_id = ctx.instance.runtime_properties["resource_id"]
            try:
                pool = conn.storagePoolLookupByName(resource_id)
            except libvirt.libvirtError as e:
                raise cfy_exc.NonRecoverableError(
                    'Failed to find the pool: {}'.format(repr(e))
                )

            # save settings
            ctx.instance.runtime_properties['params'] = template_params
            ctx.instance.runtime_properties['resource_id'] = pool.name()
            ctx.instance.runtime_properties['use_external_resource'] = True
            return

        xmlconfig = common.gen_xml_template(kwargs, template_params, 'pool')

        # create a persistent virtual pool
        pool = conn.storagePoolDefineXML(xmlconfig)
        if pool is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to create a virtual pool')

        ctx.logger.info('pool ' + pool.name() + ' has created.')
        ctx.logger.info('Params: ' + repr(template_params))
        ctx.instance.runtime_properties['params'] = template_params
        ctx.instance.runtime_properties['resource_id'] = pool.name()
        ctx.instance.runtime_properties['use_external_resource'] = False
    finally:
        conn.close()


@operation
def configure(**kwargs):
    ctx.logger.info("configure")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No pool for configure")

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
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        state, capacity, allocation, available = pool.info()
        ctx.logger.info(
            "State: {}, Capacity: {}, Allocation: {}, Available: {}"
            .format(repr(state), repr(capacity),
                    repr(allocation), repr(available)))
        if state == libvirt.VIR_STORAGE_POOL_INACTIVE:
            if pool.build(0) < 0:
                raise cfy_exc.RecoverableError(
                    'Can not build guest pool.'
                )
    finally:
        conn.close()


@operation
def start(**kwargs):
    ctx.logger.info("start")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No pool for start")

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
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        # pool create
        for i in xrange(10):
            if pool.isActive():
                ctx.logger.info("Looks as active.")
                break

            ctx.logger.info("Tring to start pool {}/10".format(i))
            if pool.create() < 0:
                raise cfy_exc.RecoverableError(
                    'Can not start pool.'
                )
            time.sleep(30)
        else:
            raise cfy_exc.RecoverableError(
                'Can not start pool.'
            )
    finally:
        conn.close()


@operation
def stop(**kwargs):
    ctx.logger.info("stop")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No pools for stop")
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
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        for i in xrange(10):
            if not pool.isActive():
                ctx.logger.info("Looks as not active.")
                break

            ctx.logger.info("Tring to stop vm {}/10".format(i))
            if pool.destroy() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not destroy pool.'
                )
            time.sleep(30)

        state, capacity, allocation, available = pool.info()
        ctx.logger.info(
            "State: {}, Capacity: {}, Allocation: {}, Available: {}"
            .format(repr(state), repr(capacity),
                    repr(allocation), repr(available)))
        if state != libvirt.VIR_STORAGE_POOL_INACTIVE:
            if pool.delete() < 0:
                raise cfy_exc.RecoverableError(
                    'Can not delete guest pool.'
                )
    finally:
        conn.close()


@operation
def delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Delete: {}".format(repr(resource_id)))

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No pool for delete")
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
        # lookup the default pool by name
        try:
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        if pool.undefine() < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not undefine pool.'
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
        raise cfy_exc.NonRecoverableError("No pool for backup")

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default pool by name
        try:
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        common.xml_snapshot_create(kwargs, resource_id, pool.XMLDesc())
    finally:
        conn.close()


@operation
def snapshot_apply(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot restore for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No pool for restore")

    libvirt_auth, _ = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default pool by name
        try:
            pool = conn.storagePoolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )

        common.xml_snapshot_apply(kwargs, resource_id, pool.XMLDesc())
    finally:
        conn.close()


@operation
def snapshot_delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot delete for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No pool for backup delete")

    common.xml_snapshot_delete(kwargs, resource_id)
