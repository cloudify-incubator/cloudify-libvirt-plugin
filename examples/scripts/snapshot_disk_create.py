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
from cloudify import exceptions as cfy_exc
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
    if not inputs.get("snapshot_name"):
        raise cfy_exc.NonRecoverableError(
            'Backup name must be provided.'
        )
    if inputs.get("snapshot_incremental"):
        ctx.logger.info("Snapshot for image automatically is created by VM "
                        "snapshot logic, check by qemu-img snapshot -l")
    else:
        backup_dir = inputs["snapshot_name"].replace("/", "_")
        if not os.path.isdir(backup_dir):
            os.makedirs(backup_dir)

        if ctx.instance.runtime_properties.get("vm_cloudinit"):
            execute_command([
                "qemu-img", "convert", "-f", "raw", "-O", "qcow2",
                ctx.instance.runtime_properties["vm_cloudinit"],
                "{}/vm_cloudinit-backup.qcow2".format(backup_dir)])
        if ctx.instance.runtime_properties.get("vm_image"):
            execute_command([
                "qemu-img", "convert", "-f", "raw", "-O", "qcow2",
                ctx.instance.runtime_properties["vm_image"],
                "{}/vm_image-backup.qcow2".format(backup_dir)])
