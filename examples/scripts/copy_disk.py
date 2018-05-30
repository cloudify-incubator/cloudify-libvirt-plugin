#!/usr/bin/env python
#
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

import os
import subprocess
from cloudify import ctx
from cloudify.state import ctx_parameters as inputs


def execute_command(command, extra_args=None):

    ctx.logger.debug('command: {0}.'.format(repr(command)))

    subprocess_args = {
        'args': command,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE
    }
    if extra_args is not None and isinstance(extra_args, dict):
        subprocess_args.update(extra_args)

    ctx.logger.debug('subprocess_args {0}.'.format(subprocess_args))

    process = subprocess.Popen(**subprocess_args)
    output, error = process.communicate()

    ctx.logger.debug('command: {0} '.format(repr(command)))
    ctx.logger.debug('output: {0} '.format(output))
    ctx.logger.debug('error: {0} '.format(error))
    ctx.logger.debug('process.returncode: {0} '.format(process.returncode))

    if process.returncode:
        ctx.logger.error('Running `{0}` returns {1} error: {2}.'
                         .format(repr(command), process.returncode,
                                 repr(error)))
        return False

    return output


if __name__ == '__main__':
    base_disk = inputs['disk_image']
    ctx.logger.debug("Base image: {}".format(repr(base_disk)))
    cloud_init = inputs['cloud_init']
    ctx.logger.debug("Cloud init: {}".format(repr(cloud_init)))
    cwd = os.getcwd()
    ctx.logger.debug("Current dir: {}".format(repr(cwd)))

    copy_disk = "{}/{}.qcow2".format(cwd, ctx.instance.id)
    execute_command(["qemu-img", "create", "-f", "qcow2", "-o",
                     "backing_file={}".format(base_disk),
                     copy_disk])

    ctx.instance.runtime_properties["vm_image"] = copy_disk

    seed_disk = "{}/{}_seed".format(cwd, ctx.instance.id)
    os.mkdir(seed_disk)
    with open("{}/meta-data".format(seed_disk), 'w') as meta_file:
        meta_file.write("instance-id: {}\n".format(ctx.instance.id))
        meta_file.write("local-hostname: {}\n".format(ctx.instance.id))

    with open("{}/user-data".format(seed_disk), 'w') as user_data:
        user_data.write(cloud_init)

    execute_command(["genisoimage", "-output", "{}.iso".format(seed_disk),
                     "-volid", "cidata",  "-joliet", "-rock",
                     "{}/user-data".format(seed_disk),
                     "{}/meta-data".format(seed_disk)])

    os.remove("{}/user-data".format(seed_disk))
    os.remove("{}/meta-data".format(seed_disk))
    os.rmdir(seed_disk)

    execute_command(["qemu-img", "convert", "-f", "raw", "-O", "qcow2",
                     "{}.iso".format(seed_disk),
                     "{}.qcow2".format(seed_disk)])

    os.remove("{}.iso".format(seed_disk))

    ctx.instance.runtime_properties[
        "vm_cloudinit"] = "{}.qcow2".format(seed_disk)
