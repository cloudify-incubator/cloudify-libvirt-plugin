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
import unittest
import mock

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.common as common


class TestCommon(LibVirtCommonTest):

    def test_get_libvirt_params(self):

        # no properties
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )
        current_ctx.set(_ctx)

        self.assertEqual(common.get_libvirt_params(), (None, {}))
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

        self.assertEqual(common.get_libvirt_params(
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

    def test_save_node_state(self):
        isdir = mock.Mock(return_value=False)
        with mock.patch(
            "os.path.isdir",
            isdir
        ):
            makedirs = mock.Mock()
            with mock.patch(
                "os.makedirs",
                makedirs
            ):
                fake_file = mock.mock_open()
                with mock.patch(
                    '__builtin__.open', fake_file
                ):
                    common.save_node_state("a", "b", "c")
                fake_file.assert_called_with('a/b.xml', 'w')
                fake_file().write.assert_called_with("c")
            makedirs.assert_called_with("a")
            isdir.assert_called_with("a")

    def test_read_node_state(self):
        # no such file
        isfile = mock.Mock(return_value=False)
        with mock.patch(
            "os.path.isfile",
            isfile
        ):
            self.assertIsNone(common.read_node_state("a", "b"))
        isfile.assert_called_with('a/b.xml')

        # read file
        isfile = mock.Mock(return_value=True)
        with mock.patch(
            "os.path.isfile",
            isfile
        ):
            fake_file = mock.mock_open()
            fake_file().read = mock.Mock(return_value=">>")
            with mock.patch(
                '__builtin__.open', fake_file
            ):
                self.assertEqual(common.read_node_state("a", "b"), ">>")
            fake_file.assert_called_with('a/b.xml', 'r')
            fake_file().read.assert_called_with()
        isfile.assert_called_with('a/b.xml')

    def test_delete_node_state(self):
        # no such file
        isfile = mock.Mock(return_value=False)
        with mock.patch(
            "os.path.isfile",
            isfile
        ):
            remove = mock.Mock()
            with mock.patch(
                "os.remove",
                remove
            ):
                common.delete_node_state("a", "b")
            remove.assert_not_called()
        isfile.assert_called_with('a/b.xml')

        # remove file
        isfile = mock.Mock(return_value=True)
        with mock.patch(
            "os.path.isfile",
            isfile
        ):
            remove = mock.Mock()
            with mock.patch(
                "os.remove",
                remove
            ):
                common.delete_node_state("a", "b")
            remove.assert_called_with('a/b.xml')
        isfile.assert_called_with('a/b.xml')


if __name__ == '__main__':
    unittest.main()
