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
import os
import uuid
from pkg_resources import resource_filename

from cloudify import ctx
from cloudify import exceptions as cfy_exc
from cloudify_common_sdk import filters
from cloudify_common_sdk._compat import text_type


def get_libvirt_params(**kwargs):
    libvirt_auth = kwargs.get('libvirt_auth')
    if not libvirt_auth:
        libvirt_auth = ctx.instance.runtime_properties.get('libvirt_auth')

    if not libvirt_auth:
        libvirt_auth = ctx.node.properties.get('libvirt_auth')

    ctx.instance.runtime_properties['libvirt_auth'] = libvirt_auth

    template_params = ctx.node.properties.get('params', {})
    template_params.update(ctx.instance.runtime_properties.get('params', {}))
    template_params.update(kwargs.get('params', {}))
    ctx.instance.runtime_properties['params'] = template_params

    # set default names and instance_uuid
    if not template_params.get("name"):
        template_params["name"] = ctx.instance.id
    if not template_params.get("instance_uuid"):
        template_params["instance_uuid"] = text_type(uuid.uuid4())

    # update 'resource_id', 'use_external_resource' from kwargs
    for field in ['resource_id', 'use_external_resource']:
        if field in kwargs:
            ctx.instance.runtime_properties[field] = kwargs[field]

    return libvirt_auth, template_params


def gen_xml_template(kwargs, template_params, default_template):
    # templates
    template_resource = kwargs.get('template_resource')
    template_content = kwargs.get('template_content')

    if template_resource:
        template_content = ctx.get_resource(template_resource)

    if not (template_resource or template_content):
        resource_dir = resource_filename(__name__, 'templates')
        template_resource = '{}/{}.xml'.format(resource_dir, default_template)
        ctx.logger.info("Will be used internal: %s" % template_resource)

    if not template_content:
        with open(template_resource) as object_desc:
            template_content = object_desc.read()

    params = {"ctx": ctx}
    if template_params:
        params.update(template_params)
    xmlconfig = filters.render_template(template_content, params)
    ctx.logger.debug(repr(xmlconfig))
    return xmlconfig


def get_backupname(kwargs):
    if not kwargs.get("snapshot_name"):
        raise cfy_exc.NonRecoverableError(
            'Backup name must be provided.'
        )
    return "{}-{}".format(ctx.instance.id, kwargs["snapshot_name"])


def get_backupdir(kwargs):
    return "{}/{}".format(
        ctx.node.properties.get('backup_dir', "."),
        kwargs["snapshot_name"].replace("/", "_")
    )


def save_node_state(backup_dir, object_name, content):
    # save object state as string
    if not os.path.isdir(backup_dir):
        os.makedirs(backup_dir)
    with open("{}/{}.xml".format(backup_dir, object_name), 'w') as file:
        file.write(content)


def read_node_state(backup_dir, object_name):
    # read object state as string
    if not os.path.isfile("{}/{}.xml".format(backup_dir, object_name)):
        return None
    with open("{}/{}.xml".format(backup_dir, object_name), 'r') as file:
        return file.read()


def delete_node_state(backup_dir, object_name):
    # read object state as string
    if not os.path.isfile("{}/{}.xml".format(backup_dir, object_name)):
        return
    os.remove("{}/{}.xml".format(backup_dir, object_name))


def get_binary_place(backup_dir, object_name):
    # return path to binary/directory place
    return "{}/{}_raw".format(backup_dir, object_name)


def check_binary_place(backup_dir, object_name):
    # check binary/directory place exists
    return os.path.isfile(get_binary_place(backup_dir, object_name))


def create_binary_place(backup_dir):
    # create binary/directory place
    if not os.path.isdir(backup_dir):
        os.makedirs(backup_dir)


def delete_binary_place(backup_dir, object_name):
    # create binary/directory place
    full_path = get_binary_place(backup_dir, object_name)
    if os.path.isfile(full_path):
        os.remove(full_path)


def xml_snapshot_create(kwargs, resource_id, current_xmldump):
    snapshot_name = get_backupname(kwargs)
    if kwargs.get("snapshot_incremental"):
        backups = ctx.instance.runtime_properties.get("backups", {})
        if snapshot_name in backups:
            raise cfy_exc.NonRecoverableError(
                "Snapshot {snapshot_name} already exists."
                .format(snapshot_name=snapshot_name,))
        backups[snapshot_name] = current_xmldump
        ctx.instance.runtime_properties["backups"] = backups
        ctx.logger.info("Snapshot {snapshot_name} is created."
                        .format(snapshot_name=snapshot_name,))
    else:
        if read_node_state(get_backupdir(kwargs), resource_id):
            raise cfy_exc.NonRecoverableError(
                "Backup {snapshot_name} already exists."
                .format(snapshot_name=snapshot_name,))
        save_node_state(get_backupdir(kwargs), resource_id, current_xmldump)
    ctx.logger.info("Backup {snapshot_name} is created."
                    .format(snapshot_name=snapshot_name,))
    ctx.logger.debug("Current config {}".format(repr(current_xmldump)))


def xml_snapshot_apply(kwargs, resource_id, current_xmldump):
    snapshot_name = get_backupname(kwargs)
    if kwargs.get("snapshot_incremental"):
        backups = ctx.instance.runtime_properties.get("backups", {})
        if snapshot_name not in backups:
            raise cfy_exc.NonRecoverableError(
                "No snapshots found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))
        xml_backup = backups[snapshot_name]
    else:
        xml_backup = read_node_state(get_backupdir(kwargs), resource_id)
        if not xml_backup:
            raise cfy_exc.NonRecoverableError(
                "No backups found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))

    if xml_backup.strip() != current_xmldump.strip():
        ctx.logger.info("We have different configs,\n{}\nvs\n{}\n"
                        .format(
                            repr(xml_backup.strip()),
                            repr(current_xmldump.strip())))
    else:
        ctx.logger.info("Already used such configuration: {}"
                        .format(snapshot_name))


def xml_snapshot_delete(kwargs, resource_id):
    snapshot_name = get_backupname(kwargs)
    if kwargs.get("snapshot_incremental"):
        backups = ctx.instance.runtime_properties.get("backups", {})
        if snapshot_name not in backups:
            raise cfy_exc.NonRecoverableError(
                "No snapshots found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))
        del backups[snapshot_name]
        ctx.instance.runtime_properties["backups"] = backups
    else:
        if not read_node_state(get_backupdir(kwargs), resource_id):
            raise cfy_exc.NonRecoverableError(
                "No backups found with name: {snapshot_name}."
                .format(snapshot_name=snapshot_name,))
        delete_node_state(get_backupdir(kwargs), resource_id)
    ctx.logger.info("Backup deleted: {}".format(snapshot_name))
