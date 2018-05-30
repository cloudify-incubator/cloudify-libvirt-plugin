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
import mock

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.network_tasks as network_tasks


class TestNetworkTasks(LibVirtCommonTest):

    def test_unlink(self):
        _target = MockCloudifyContext(
            'target',
            properties={},
            runtime_properties={
                'resource_id': 'target_id',
                'name': 'target',
                'ip': '1.2.3.4'
            }
        )
        _source = MockCloudifyContext(
            'source',
            properties={},
            runtime_properties={
                'resource_id': 'source_id',
                'name': 'source'
            }
        )

        _ctx = MockCloudifyContext(
            target=_target,
            source=_source
        )
        current_ctx.set(_ctx)

        network_tasks.unlink(ctx=_ctx)

        self.assertEqual(_source.instance.runtime_properties, {
            'resource_id': 'source_id',
            'name': 'source'})
        self.assertEqual(_target.instance.runtime_properties, {
            'ip': None,
            'resource_id': 'target_id',
            'name': 'target'})

    def test_link(self):
        _target = MockCloudifyContext(
            'target',
            properties={},
            runtime_properties={
                'resource_id': 'target_id',
                'name': 'target',
                'ip': '1.2.3.4'
            }
        )
        _source = MockCloudifyContext(
            'source',
            properties={},
            runtime_properties={
                'resource_id': 'source_id',
                'name': 'source',
                'params': {
                    "networks": [{
                        'mac': "ab:cd:ef"
                    }]
                }
            }
        )

        _ctx = MockCloudifyContext(
            target=_target,
            source=_source
        )
        current_ctx.set(_ctx)

        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.link, [], {'ctx': _ctx})

        # check correct handle exception with unexisted object
        self._check_no_such_object_network(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.link, [], {'ctx': _ctx}, 'target_id')

        # no leases
        network = mock.Mock()
        network.destroy = mock.Mock(return_value=-1)
        network.DHCPLeases = mock.Mock(return_value=[])
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)

        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "time.sleep",
                mock.Mock(return_value=None)
            ):
                with self.assertRaisesRegexp(
                    RecoverableError,
                    'No ip for now, try later'
                ):
                    network_tasks.link(ctx=_ctx)

        # lease
        network.DHCPLeases = mock.Mock(return_value=[{
            'mac': "ab:cd:ef",
            'ipaddr': "1.2.3.4"
        }])
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "time.sleep",
                mock.Mock(return_value=None)
            ):
                network_tasks.link(ctx=_ctx)
        self.assertEqual(
            _ctx.source.instance.runtime_properties['ip'],
            "1.2.3.4"
        )

    def test_delete(self):
        self._test_no_resource_id(network_tasks.delete)

        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.delete, [], {'ctx': _ctx})

        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_network(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.delete, [], {'ctx': _ctx}, 'resource')

        # delete with error
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        network = mock.Mock()
        network.destroy = mock.Mock(return_value=-1)
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Can not undefine network.'
            ):
                network_tasks.delete(ctx=_ctx)
        connect.networkLookupByName.assert_called_with('resource')

        # delete without error
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        network = mock.Mock()
        network.destroy = mock.Mock(return_value=0)
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
                network_tasks.delete(ctx=_ctx)
        self.assertFalse(_ctx.instance.runtime_properties.get('resource_id'))

    def _create_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={
                'libvirt_auth': {'a': 'c'}
            },
            runtime_properties={
                'libvirt_auth': {'a': 'd'}
            }
        )
        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.create, [], {'ctx': _ctx})

        # check error with create network
        _ctx = self._create_ctx()
        self._check_create_object(
            'Failed to create a virtual network',
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.create, [], {'ctx': _ctx})

        # create network
        network = mock.Mock()
        network.isActive = mock.Mock(return_value=1)
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkCreateXML = mock.Mock(return_value=network)

        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.create(ctx=_ctx, network_file="domain_file")
        connect.networkCreateXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "network_name"
        )

        # unactive
        network.isActive = mock.Mock(return_value=0)
        connect.networkCreateXML = mock.Mock(return_value=network)

        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.create(ctx=_ctx, network_file="domain_file")
        connect.networkCreateXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "network_name"
        )
