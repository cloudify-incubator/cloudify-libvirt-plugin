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

import subprocess
from cloudify import ctx


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

    runtime_properties = ctx.instance.runtime_properties
    internal_ip = runtime_properties.get("internal_ip")
    external_ip = runtime_properties.get("external_ip")
    external_interface = runtime_properties.get("external_interface")

    if external_ip and internal_ip and external_interface:
        execute_command(["sudo", "/sbin/ip", "address",
                         "del", "{}/24".format(external_ip),
                         "dev", external_interface])
        execute_command(["sudo", "/sbin/iptables", "-D", "FORWARD",
                         "-d", internal_ip, "-j", "ACCEPT"])
        execute_command(["sudo", "/sbin/iptables", "-D", "PREROUTING",
                         "-t", "nat", "-d", external_ip,
                         "-j", "DNAT", "--to-destination", internal_ip])
