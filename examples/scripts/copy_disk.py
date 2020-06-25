#!/usr/bin/env python
#
# Copyright (c) 2017-2019 Cloudify Platform Ltd. All rights reserved
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
#

import re
import os
import subprocess
from cloudify import ctx
from cloudify import exceptions

MAX_HOSTNAME = 63
ID_HASH_CONST = 6


def execute_command(command, extra_args=None):

    ctx.logger.debug(f'command: {repr(command)}.')

    subprocess_args = {
        'args': command,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE
    }
    if extra_args is not None and isinstance(extra_args, dict):
        subprocess_args.update(extra_args)

    ctx.logger.debug(f'subprocess_args {subprocess_args}.')

    process = subprocess.Popen(**subprocess_args)
    output, error = process.communicate()

    ctx.logger.debug(f'command: {repr(command)} ')
    ctx.logger.debug(f'output: {output} ')
    ctx.logger.debug(f'error: {error} ')
    ctx.logger.debug(f'process.returncode: {process.returncode} ')

    if process.returncode:
        ctx.logger.error('Running `{0}` returns {1} error: {2}.'
                         .format(repr(command), process.returncode,
                                 repr(error)))
        return False

    return output


def _gen_hostname(name):
    # replace underscores with hyphens
    final_name = name.replace('_', '-')
    # remove all non-alphanumeric characters except hyphens
    final_name = re.sub(r'[^a-zA-Z0-9-]+', '', final_name)
    # assure the first character is alpha
    if not final_name[0].isalpha():
        final_name = '{0}{1}'.format('a', final_name)
    # trim to the length limit
    if len(final_name) > MAX_HOSTNAME:
        remain_len = MAX_HOSTNAME - len(final_name)
        final_name = '{0}{1}'.format(
            final_name[:remain_len - ID_HASH_CONST],
            final_name[-ID_HASH_CONST:])
    # remove dash at the end
    while len(final_name) and final_name[-1] == "-":
        final_name = final_name[:-1]
    # convert string to lowercase
    final_name = final_name.lower()
    return final_name


if __name__ == '__main__':
    base_disk = ctx.instance.runtime_properties['disk_image']
    ctx.logger.info(f"Base image: {repr(base_disk)}")
    cloud_init = ctx.instance.runtime_properties['cloud_init']
    ctx.logger.debug(f"Cloud init: {repr(cloud_init)}")
    cwd = ctx.instance.runtime_properties.get('storage_path', os.getcwd())
    ctx.logger.info(f"Current dir: {repr(cwd)}")

    copy_disk = f"{cwd}/{ctx.instance.id}.qcow2"
    if not execute_command([
        "qemu-img", "create", "-f", "qcow2", "-o",
        f"backing_file={base_disk}", copy_disk
    ]):
        raise exceptions.RecoverableError('Failed create disk.')
    if ctx.instance.runtime_properties.get('disk_size'):
        if not execute_command([
            "qemu-img", "resize", copy_disk,
            ctx.instance.runtime_properties.get('disk_size')
        ]):
            raise exceptions.RecoverableError('Failed resize disk.')

    ctx.instance.runtime_properties["vm_image"] = copy_disk

    seed_disk = f"{cwd}/{ctx.instance.id}_seed"
    os.mkdir(seed_disk)
    with open(f"{seed_disk}/meta-data", 'w') as meta_file:
        meta_file.write(f"instance-id: {ctx.instance.id}\n")
        meta_file.write(f"local-hostname: {_gen_hostname(ctx.instance.id)}\n")

    ctx.logger.debug(f"cloud init:\n===\n{cloud_init}\n===\n")
    with open(f"{seed_disk}/user-data", 'w') as user_data:
        user_data.write(cloud_init)

    if not execute_command([
        "genisoimage", "-output", f"{seed_disk}.iso",
        "-volid", "cidata",  "-joliet", "-rock",
        f"{seed_disk}/user-data",
        f"{seed_disk}/meta-data"
    ]):
        raise exceptions.RecoverableError('Failed create iso.')

    os.remove(f"{seed_disk}/user-data")
    os.remove(f"{seed_disk}/meta-data")
    os.rmdir(seed_disk)

    if not execute_command([
        "qemu-img", "convert", "-f", "raw", "-O", "qcow2",
        f"{seed_disk}.iso", f"{seed_disk}.qcow2"
    ]):
        raise exceptions.RecoverableError('Failed convert qcow image')

    os.remove(f"{seed_disk}.iso")

    ctx.instance.runtime_properties["vm_cloudinit"] = f"{seed_disk}.qcow2"
