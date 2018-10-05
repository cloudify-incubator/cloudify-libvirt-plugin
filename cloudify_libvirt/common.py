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
import os
from cloudify import ctx
from cloudify import exceptions as cfy_exc


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
    return libvirt_auth, template_params


def get_backupname(kwargs):
    if not kwargs.get("snapshot_name"):
        raise cfy_exc.NonRecoverableError(
            'Backup name must be provided.'
        )
    return kwargs["snapshot_name"]


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
