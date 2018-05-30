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

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
from cloudify_libvirt.common import get_libvirt_params


class TestCommon(LibVirtCommonTest):

    def test_get_libvirt_params(self):

        # no properties
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )
        current_ctx.set(_ctx)

        self.assertEqual(get_libvirt_params(), (None, {}))
        self.assertEqual(_ctx.instance.runtime_properties, {
            'libvirt_auth': None,
            'params': {}
        })

        # overwrite
        _ctx = MockCloudifyContext(
            'node_name',
            properties={
                'params': {'a': "b", 'c': 'g'},
                'libvirt_auth': {'a': 'c'}
            },
            runtime_properties={
                'params': {'c': "d", 'e': 'g'},
                'libvirt_auth': {'a': 'd'}
            }
        )
        current_ctx.set(_ctx)

        self.assertEqual(get_libvirt_params(
            params={'z': 'y'}, libvirt_auth={'w': 'x'}
        ), ({
                'w': 'x'
            }, {
                'a': 'b',
                'c': 'd',
                'e': 'g',
                'z': 'y'
            })
        )
        self.assertEqual(_ctx.instance.runtime_properties, {
            'libvirt_auth': {'w': 'x'},
            'params': {'a': 'b', 'c': 'd', 'e': 'g', 'z': 'y'}
        })
