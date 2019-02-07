########
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
import pycdlib
import os
import re
from io import BytesIO

from cloudify import ctx
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
import cloudify_libvirt.common as common


def _joliet_name(name):
    if name[0] == "/":
        name = name[1:]
    return "/{}".format(name[:64])


def _name_cleanup(name):
    return re.sub('[^A-Z0-9_]{1}', r'_', name.upper())


def _iso_name(name):
    if name[0] == "/":
        name = name[1:]

    name_splited = name.split('.')
    if len(name_splited[-1]) <= 3 and len(name_splited) > 1:
        return "/{}.{};1".format(
            _name_cleanup("_".join(name_splited[:-1])[:8]),
            _name_cleanup(name_splited[-1]))
    else:
        return "/{}.;1".format(_name_cleanup(name[:8]))


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
                'Failed to find the volume: {}'.format(repr(e))
            )

        iso = pycdlib.PyCdlib()
        iso.new(vol_ident='cidata', joliet=3, rock_ridge='1.09')

        fstree = template_params.get('files', {})
        for name in fstree:
            file_bufer = BytesIO()
            file_bufer.write(fstree[name].encode())
            iso.add_fp(file_bufer, len(fstree[name]),
                       _iso_name(name), rr_name=name,
                       joliet_path=_joliet_name(name))

        outiso = BytesIO()
        iso.write_fp(outiso)
        outiso.seek(0, os.SEEK_END)
        iso_size = outiso.tell()
        iso.close()

        ctx.logger.info("ISO size: {}".format(repr(iso_size)))

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
