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
import mock
import unittest

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError

from cloudify_common_sdk._compat import builtins_open

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

    def _test_empty_connection(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            func, [], {'ctx': _ctx})

    def _test_empty_connection_backup(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"})

    def _test_empty_network(self, func):
        # check correct handle exception with empty network
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_network(
            "cloudify_libvirt.network_tasks.libvirt.open",
            func, [], {'ctx': _ctx}, 'resource')

    def test_reuse_network_create_not_exist(self):
        # check correct handle exception with empty network
        _ctx = self._create_ctx()
        self._check_no_such_object_network(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.create, [], {
                'ctx': _ctx,
                "resource_id": 'resource',
                "use_external_resource": True,
            }, 'resource')

    def test_reuse_network_create_exist(self):
        # check that we can use network
        _ctx = self._create_ctx()

        network = mock.Mock()
        network.name = mock.Mock(return_value="resource")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.create(ctx=_ctx,
                                 resource_id='resource',
                                 use_external_resource=True)
        connect.networkLookupByName.assert_called_with('resource')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], 'resource'
        )
        self.assertTrue(
            _ctx.instance.runtime_properties['use_external_resource']
        )

    def _test_empty_network_backup(self, func):
        # check correct handle exception with empty network
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_network(
            "cloudify_libvirt.network_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"}, 'resource')

    def _create_fake_network_backup(self):
        network = mock.Mock()
        network.XMLDesc = mock.Mock(return_value="<network/>")
        network.isActive = mock.Mock(return_value=1)
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        _ctx.instance.runtime_properties["backups"] = {
            "node_name-backup": "<xml/>"}
        return _ctx, connect, network

    def test_snapshot_apply(self):
        self._test_no_resource_id(network_tasks.snapshot_apply,
                                  "No network for restore")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.snapshot_apply)
        self._test_empty_connection_backup(network_tasks.snapshot_apply)
        self._test_empty_network_backup(network_tasks.snapshot_apply)

        # no such snapshot
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                network_tasks.snapshot_apply(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)

        # we have such snapshot
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.snapshot_apply(
                ctx=_ctx, snapshot_name="backup",
                snapshot_incremental=True)

        # no such backup
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=False)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "No backups found with name: node_name-backup!."
                ):
                    network_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # have backup
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "<network/>"
                with mock.patch(
                    builtins_open, fake_file
                ):
                    network_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)
                fake_file.assert_called_with('./backup!/resource.xml', 'r')

    def test_snapshot_create(self):
        self._test_no_resource_id(network_tasks.snapshot_create,
                                  "No network for backup")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.snapshot_create)
        self._test_empty_connection_backup(network_tasks.snapshot_create)
        self._test_empty_network_backup(network_tasks.snapshot_create)

        # check create snapshot with error, already exists
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Snapshot node_name-backup already exists."
            ):
                network_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                              snapshot_incremental=True)
        connect.networkLookupByName.assert_called_with('resource')

        # no such snapshots
        _ctx.instance.runtime_properties["backups"] = {}
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                          snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {"node_name-backup": "<network/>"})

        # check create snapshot
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isdir",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "!!!!"
                with mock.patch(
                    builtins_open, fake_file
                ):
                    # with error, already exists
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=True)
                    ):
                        with self.assertRaisesRegexp(
                            NonRecoverableError,
                            "Backup node_name-backup already exists."
                        ):
                            network_tasks.snapshot_create(
                                ctx=_ctx, snapshot_name="backup",
                                snapshot_incremental=False)
                    # without error
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=False)
                    ):
                        network_tasks.snapshot_create(
                            ctx=_ctx, snapshot_name="backup",
                            snapshot_incremental=False)
                    fake_file().write.assert_called_with("<network/>")

    def test_snapshot_delete(self):
        self._test_no_resource_id(network_tasks.snapshot_delete,
                                  "No network for backup delete")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.snapshot_delete)

        # no such snapshots
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                network_tasks.snapshot_delete(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {'node_name-backup': "<xml/>"})

        # remove snapshot
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.snapshot_delete(ctx=_ctx, snapshot_name="backup",
                                          snapshot_incremental=True)
        self.assertEqual(_ctx.instance.runtime_properties["backups"], {})

        # no such backup
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=False)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "No backups found with name: node_name-backup!."
                ):
                    network_tasks.snapshot_delete(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # remove backup
        _ctx, connect, network = self._create_fake_network_backup()
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "!!!!"
                remove_mock = mock.Mock()
                with mock.patch(
                    "os.remove",
                    remove_mock
                ):
                    with mock.patch(
                        builtins_open, fake_file
                    ):
                        network_tasks.snapshot_delete(
                            ctx=_ctx, snapshot_name="backup!",
                            snapshot_incremental=False)
                    fake_file.assert_called_with('./backup!/resource.xml', 'r')
                remove_mock.assert_called_with('./backup!/resource.xml')

    def test_delete(self):
        self._test_no_resource_id(network_tasks.delete)
        self._test_empty_connection(network_tasks.delete)
        self._test_empty_network(network_tasks.delete)
        self._test_reused_object(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.delete)

        # delete with error
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties["backups"] = {
            "node_name-backup": "<xml/>"}

        network = mock.Mock()
        network.destroy = mock.Mock(return_value=-1)
        network.name = mock.Mock(return_value="network_name")

        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(return_value=network)
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
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
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.delete(ctx=_ctx)
        self.assertFalse(_ctx.instance.runtime_properties.get('resource_id'))
        self.assertFalse(_ctx.instance.runtime_properties.get("backup"))

    def test_create(self):
        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.create, [], {'ctx': self._create_ctx()})

        # check error with create network
        self._check_create_object(
            'Failed to create a virtual network',
            "cloudify_libvirt.network_tasks.libvirt.open",
            network_tasks.create, [], {'ctx': self._create_ctx()})

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
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.create(ctx=_ctx,
                                 template_resource="template_resource")
        connect.networkCreateXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "network_name"
        )
        self.assertFalse(
            _ctx.instance.runtime_properties['use_external_resource']
        )

        # unactive
        network.isActive = mock.Mock(return_value=0)
        connect.networkCreateXML = mock.Mock(return_value=network)

        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            network_tasks.create(ctx=_ctx,
                                 template_resource="template_resource")
        connect.networkCreateXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "network_name"
        )

        # rerun on created
        connect.networkLookupByName = mock.Mock(
            side_effect=network_tasks.libvirt.libvirtError("e"))
        with mock.patch(
            "cloudify_libvirt.network_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the network.'
            ):
                network_tasks.create(ctx=_ctx,
                                     template_resource="template_resource")


if __name__ == '__main__':
    unittest.main()
