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

import subprocess
from cloudify import ctx
try:
    import distro
except ImportError:
    import os
    p = os.popen("pip install --user distro")
    output = p.read()
    import distro


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
                         .format(repr(command),
                                 process.returncode,
                                 repr(error))
                        )
        return False

    return output


if __name__ == '__main__':
    execute_command(["uname", "-a"])

    ctx.logger.info('Installing freeze requirements.')
    linux_distro = ctx.node.properties.get('linux_distro')

    if not linux_distro:
        linux_distro_raw = distro.linux_distribution(full_distribution_name=False)[0]
        linux_distro = linux_distro_raw.lower()

    if ('centos' in linux_distro) or ('redhat' in linux_distro):
        execute_command(["sudo", "yum", "install", "util-linux", "-y"])
    elif ('ubuntu' in linux_distro) or ('debian' in linux_distro):
        execute_command(["sudo", "apt-get", "install", "util-linux", "-y"])
    else:
        ctx.logger.info('Unsupported platform.')
