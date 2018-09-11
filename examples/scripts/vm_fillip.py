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
from cloudify import ctx

if __name__ == '__main__':
    runtime_properties = ctx.instance.runtime_properties
    for relationship in ctx.instance.relationships:
        if relationship.type in [
            'cloudify.relationships.contained_in',
            'cloudify.relationships.depends_on'
        ]:
            prop = relationship.target.instance.runtime_properties
            ip = prop.get('ip')
            if ip:
                runtime_properties['private_ip'] = ip
            ip = prop.get("internal_ip")
            if ip:
                runtime_properties['private_ip'] = ip
            public_ip = prop.get("external_ip")
            if public_ip:
                runtime_properties['public_ip'] = public_ip
            elif ip:
                runtime_properties['public_ip'] = ip

    if ctx.node.properties.get("use_public_ip"):
        runtime_properties['ip'] = runtime_properties['public_ip']
    else:
        runtime_properties['ip'] = runtime_properties['private_ip']
