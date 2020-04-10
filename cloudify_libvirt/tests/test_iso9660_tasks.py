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
import unittest
import mock

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.iso9660_tasks as iso9660_tasks


class TestIso9660Task(LibVirtCommonTest):

    def test_create(self):
        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.iso9660_tasks.libvirt.open",
            iso9660_tasks.create, [], {'ctx': self._create_ctx()})

        # check error with create iso image
        self._check_create_object(
            'Failed to find the volume',
            "cloudify_libvirt.iso9660_tasks.libvirt.open",
            iso9660_tasks.create, [], {'ctx': self._create_ctx(),
                                       'params': {'pool': 'empty'}})

        volume = mock.Mock()
        pool = mock.Mock()
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)

        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.iso9660_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            iso9660_tasks.create(ctx=_ctx, params={
                "pool": "_+pool",
                "volume": "_+volume",
                "files": {
                    "meta-data": "instance-id: localhost"
                }
            })
        connect.storagePoolLookupByName.assert_called_with("_+pool")
        pool.storageVolLookupByName.assert_called_with("_+volume")


if __name__ == '__main__':
    unittest.main()
