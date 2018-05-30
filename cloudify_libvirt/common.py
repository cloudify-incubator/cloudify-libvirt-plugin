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
from cloudify import ctx


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
