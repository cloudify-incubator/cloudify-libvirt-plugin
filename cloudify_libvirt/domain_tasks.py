########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import libvirt
import time
import uuid
from lxml import etree

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import utils


@operation
def create(**kwargs):
    ctx.logger.info("create")

    domain = kwargs.get('domain', {})

    if not domain.get("name"):
        domain["name"] = ctx.instance.id
    if not domain.get("uuid"):
        domain["uuid"] = str(uuid.uuid4())

    ctx.instance.runtime_properties['domain'] = domain

@operation
def configure(**kwargs):
    ctx.logger.info("configure")


@operation
def start(**kwargs):
    ctx.logger.info("start")


@operation
def stop(**kwargs):
    ctx.logger.info("stop")


@operation
def delete(**kwargs):
    ctx.logger.info("delete")
