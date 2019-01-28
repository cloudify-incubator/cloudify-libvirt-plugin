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


@operation
def create(**kwargs):
    ctx.logger.info("Creating new volume.")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the pool: {}'.format(repr(e))
            )
        if ctx.instance.runtime_properties.get("use_external_resource"):
            # lookup the default volume by name
            resource_id = ctx.instance.runtime_properties["resource_id"]
            try:
                volume = pool.storageVolLookupByName(resource_id)
            except libvirt.libvirtError as e:
                raise cfy_exc.NonRecoverableError(
                    'Failed to find the volume: {}'.format(repr(e))
                )

            # save settings
            template_params['path'] = volume.path()
            ctx.instance.runtime_properties['params'] = template_params
            ctx.instance.runtime_properties['resource_id'] = volume.name()
            ctx.instance.runtime_properties['use_external_resource'] = True
            return

        xmlconfig = common.gen_xml_template(kwargs, template_params, 'volume')

        # create a persistent virtual volume
        volume = pool.createXML(xmlconfig)
        if volume is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to create a virtual volume')

        ctx.logger.info('volume ' + volume.name() + ' has created.')
        ctx.logger.info('Params: ' + repr(template_params))
        template_params['path'] = volume.path()
        ctx.instance.runtime_properties['params'] = template_params
        ctx.instance.runtime_properties['resource_id'] = volume.name()
        ctx.instance.runtime_properties['use_external_resource'] = False
    finally:
        conn.close()


@operation
def start(**kwargs):
    ctx.logger.info("start")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No volumes for zero")
        return

    if ctx.instance.runtime_properties.get('use_external_resource'):
        ctx.logger.info("External resource, skip")
        return

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the volume: {}'.format(repr(e))
            )

        if (
            template_params.get('zero_wipe') and
            template_params.get('allocation')
        ):
            allocation = int(template_params.get('allocation', 0))
            allocation *= 1024  # KB
            stream = conn.newStream(0)
            volume.upload(stream, 0, allocation * 1024, 0)
            zero_buff = "\0" * 1024
            for i in xrange(allocation):
                stream.send(zero_buff)
            stream.finish()

    finally:
        conn.close()


@operation
def stop(**kwargs):
    ctx.logger.info("stop")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No volumes for stop")
        return

    if ctx.instance.runtime_properties.get('use_external_resource'):
        ctx.logger.info("External resource, skip")
        return

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the volume: {}'.format(repr(e))
            )

        for i in xrange(10):
            ctx.logger.info("Tring to wipe vm {}/10".format(i))
            if volume.wipe(0) == 0:
                break
            time.sleep(30)

    finally:
        conn.close()


@operation
def delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Delete: {}".format(repr(resource_id)))

    if not resource_id:
        # not raise exception on 'uninstall' workflow
        ctx.logger.info("No volume for delete")
        return

    if ctx.instance.runtime_properties.get('use_external_resource'):
        ctx.logger.info("External resource, skip")
        return

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the volume: {}'.format(repr(e))
            )

        if volume.delete(0) < 0:
            raise cfy_exc.NonRecoverableError(
                'Can not undefine volume.'
            )

        ctx.instance.runtime_properties['resource_id'] = None
        ctx.instance.runtime_properties['backups'] = {}
        ctx.instance.runtime_properties['params'] = {}
    finally:
        conn.close()


@operation
def snapshot_create(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot create: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No volume for backup")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the volume: {}'.format(repr(e))
            )

        common.xml_snapshot_create(kwargs, resource_id, volume.XMLDesc())
    finally:
        conn.close()


@operation
def snapshot_apply(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot restore for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No volume for restore")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(resource_id)
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the volume: {}'.format(repr(e))
            )

        common.xml_snapshot_apply(kwargs, resource_id, volume.XMLDesc())
    finally:
        conn.close()


@operation
def snapshot_delete(**kwargs):
    resource_id = ctx.instance.runtime_properties.get('resource_id')
    ctx.logger.info("Snapshot delete for: {}".format(repr(resource_id)))

    if not resource_id:
        # not uninstall workflow, raise exception
        raise cfy_exc.NonRecoverableError("No volume for backup delete")

    common.xml_snapshot_delete(kwargs, resource_id)
