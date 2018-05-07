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

from jinja2 import Template
from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
from pkg_resources import resource_filename
from cloudify_libvirt.common import get_libvirt_params


@operation
def create(**kwargs):
    ctx.logger.info("create")
    get_libvirt_params(**kwargs)
    # dont need to run anything, we attach disc's in preconfigure state
    # so we will define domain later


@operation
def configure(**kwargs):
    ctx.logger.info("configure")

    libvirt_auth, template_params = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    domain_file = kwargs.get('domain_file')
    domain_template = kwargs.get('domain_template')

    if domain_file:
        domain_template = ctx.get_resource(domain_file)

    if not domain_file and not domain_template:
        resource_dir = resource_filename(__name__, 'templates')
        domain_file = '{}/domain.xml'.format(resource_dir)
        ctx.logger.info("Will be used internal: %s" % domain_file)

    if not domain_template:
        domain_desc = open(domain_file)
        with domain_desc:
            domain_template = domain_desc.read()

    template_engine = Template(domain_template)
    if not template_params:
        template_params = {}

    if not template_params.get("resource_id"):
        template_params["resource_id"] = ctx.instance.id
    if (not template_params.get("memory_minsize") and
            template_params.get('memory_size')):
        # if have no minimal memory size, set current as minimum
        # and twised memory as maximum
        memory_size = int(template_params['memory_size'])
        template_params["memory_minsize"] = memory_size
        template_params['memory_size'] = memory_size * 2
    if not template_params.get("instance_uuid"):
        template_params["instance_uuid"] = str(uuid.uuid4())

    params = {"ctx": ctx}
    params.update(template_params)
    xmlconfig = template_engine.render(params)

    ctx.logger.info(repr(xmlconfig))

    dom = conn.defineXML(xmlconfig)
    if dom is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to define a domain from an XML definition.'
        )

    ctx.instance.runtime_properties['resource_id'] = dom.name()

    if dom.create() < 0:
        raise cfy_exc.NonRecoverableError(
            'Can not boot guest domain.'
        )
    conn.close()

    ctx.logger.info('Guest ' + dom.name() + ' has booted')
    ctx.instance.runtime_properties['resource_id'] = dom.name()
    ctx.instance.runtime_properties['params'] = template_params


@operation
def start(**kwargs):
    ctx.logger.info("start")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for start")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, reason = dom.state()
        for i in xrange(10):
            state, reason = dom.state()

            if state == libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as running.")
                return

            ctx.logger.info("Tring to start vm {}/10".format(i))
            if dom.create() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not start guest domain.'
                )
            time.sleep(30)
            state, reason = dom.state()
    finally:
        conn.close()


@operation
def stop(**kwargs):
    ctx.logger.info("stop")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, reason = dom.state()
        for i in xrange(10):
            state, reason = dom.state()

            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info("Tring to stop vm {}/10".format(i))
            if dom.shutdown() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not shutdown guest domain.'
                )
            time.sleep(30)
            state, reason = dom.state()
    finally:
        conn.close()


@operation
def resume(**kwargs):
    ctx.logger.info("resume")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for resume")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, reason = dom.state()
        for i in xrange(10):
            state, reason = dom.state()

            if state == libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as running.")
                return

            ctx.logger.info("Tring to resume vm {}/10".format(i))
            if dom.resume() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not suspend guest domain.'
                )
            time.sleep(30)
            state, reason = dom.state()
    finally:
        conn.close()


@operation
def suspend(**kwargs):
    ctx.logger.info("suspend")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for suspend")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, reason = dom.state()
        for i in xrange(10):
            state, reason = dom.state()

            if state != libvirt.VIR_DOMAIN_RUNNING:
                ctx.logger.info("Looks as not run.")
                return

            ctx.logger.info("Tring to suspend vm {}/10".format(i))
            if dom.suspend() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not suspend guest domain.'
                )
            time.sleep(30)
            state, reason = dom.state()
    finally:
        conn.close()


@operation
def delete(**kwargs):
    ctx.logger.info("delete")

    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for delete")
        return

    libvirt_auth, _ = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        state, reason = dom.state()

        if state != libvirt.VIR_DOMAIN_SHUTOFF:
            if dom.destroy() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not destroy guest domain.'
                )

        try:
            if dom.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_NVRAM) < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not undefine guest domain with NVRAM.'
                )
        except AttributeError as e:
            ctx.logger.info("Non critical error: {}".format(str(e)))
            if dom.undefine() < 0:
                raise cfy_exc.NonRecoverableError(
                    'Can not undefine guest domain.'
                )
    finally:
        conn.close()


def _current_use(dom):
    total_list = dom.getCPUStats(True)
    if len(total_list):
        total = total_list[0]
    else:
        total = {}
    return (
        total.get('user_time', 0) + total.get('system_time', 0) +
        total.get('cpu_time', 0)
    ) / 1000000000.0


@operation
def perfomance(**kwargs):
    ctx.logger.info("update statistics")
    resource_id = ctx.instance.runtime_properties.get('resource_id')

    if not resource_id:
        ctx.logger.info("No servers for statistics.")
        return

    libvirt_auth, template_params = get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        try:
            dom = conn.lookupByName(resource_id)
        except Exception as e:
            dom = None
            ctx.logger.info("Non critical error: {}".format(str(e)))

        if dom is None:
            raise cfy_exc.NonRecoverableError(
                'Failed to find the domain'
            )

        statistics = ctx.instance.runtime_properties.get('stat', {})

        before_usage = _current_use(dom)

        # usage generated by compare cpu_time before
        # and after sleep for 5 seconds.
        ctx.logger.debug("Used: {} seconds.".format(before_usage))
        time.sleep(5)
        statistics['cpu'] = 100 * (_current_use(dom) - before_usage) / 5

        memory = dom.memoryStats()
        statistics['memory'] = memory.get('actual', 0) / 1024.0
        ctx.instance.runtime_properties['stat'] = statistics

        ctx.logger.info("Statistics: {}".format(repr(statistics)))
    finally:
        conn.close()
