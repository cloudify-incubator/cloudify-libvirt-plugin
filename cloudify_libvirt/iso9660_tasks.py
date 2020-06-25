# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
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

import libvirt
import os

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import cloudify_common_sdk.iso9660 as iso9660

import cloudify_libvirt.common as common


@operation
def create(**kwargs):
    ctx.logger.info("Creating new iso image.")

    libvirt_auth, template_params = common.get_libvirt_params(**kwargs)
    conn = libvirt.open(libvirt_auth)
    if conn is None:
        raise cfy_exc.NonRecoverableError(
            'Failed to open connection to the hypervisor'
        )

    try:
        # lookup the default volume by name
        try:
            pool = conn.storagePoolLookupByName(template_params["pool"])
            volume = pool.storageVolLookupByName(template_params["volume"])
        except libvirt.libvirtError as e:
            raise cfy_exc.NonRecoverableError(
                f'Failed to find the volume: {repr(e)}'
            )

        outiso = iso9660.create_iso(
            vol_ident=template_params.get('vol_ident', 'cidata'),
            sys_ident=template_params.get('sys_ident', ""),
            get_resource=ctx.get_resource,
            files=template_params.get('files', {}),
            files_raw=template_params.get('files_raw', {}))

        outiso.seek(0, os.SEEK_END)
        iso_size = outiso.tell()
        outiso.seek(0, os.SEEK_SET)

        ctx.logger.info(f"ISO size: {repr(iso_size)}")

        stream = conn.newStream(0)
        volume.upload(stream, 0, iso_size, 0)
        outiso.seek(0, os.SEEK_SET)

        read_size = iso_size
        while read_size > 0:
            buffer = outiso.read(read_size)
            read_size -= len(buffer)
            stream.send(buffer)
        stream.finish()

    finally:
        conn.close()
