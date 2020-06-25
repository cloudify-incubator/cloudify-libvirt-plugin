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

import os
import netifaces
import subprocess
from cloudify import ctx


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


if __name__ == '__main__':
    external_ip_slist = os.environ['EXTERNAL_IP']
    internal_ip = os.environ['INTERNAL_IP']
    external_interface = os.environ['EXTERNAL_INTERFACE']

    used_ips = []
    addreses = netifaces.ifaddresses(external_interface)
    for inet_type in addreses:
        for addres_info in addreses[inet_type]:
            used_ips.append(addres_info['addr'])
    ctx.logger.debug(f'Already used: {used_ips}')

    external_ips = external_ip_slist.strip().split(',')

    for check_ip in external_ips:
        ctx.logger.debug(f'Check for use: {check_ip}')
        if check_ip in used_ips:
            continue
        external_ip = check_ip
        break

    ctx.logger.info(f'Will be used: {external_ip}')

    # add ip alias
    execute_command(["sudo", "/sbin/ip", "address", "add",
                     "{}/24".format(external_ip), "dev",
                     external_interface])

    # add iptables rules
    execute_command(["sudo", "/sbin/iptables", "-t", "nat",
                     "-I", "PREROUTING", "-d", external_ip,
                     "-j", "DNAT", "--to-destination", internal_ip])

    execute_command(["sudo", "/sbin/iptables", "-I", "FORWARD",
                     "-d",  internal_ip, "-j", "ACCEPT"])

    ctx.instance.runtime_properties["internal_ip"] = internal_ip
    ctx.instance.runtime_properties["external_ip"] = external_ip
    ctx.instance.runtime_properties["external_interface"] = external_interface
