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
import mock
import unittest

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.pool_tasks as pool_tasks


class TestPoolTasks(LibVirtCommonTest):

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

    def _test_empty_connection_backup(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"})

    def _test_empty_pool(self, func):
        # check correct handle exception with empty volume
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}
        self._check_no_such_object_pool(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            func, [], {'ctx': _ctx}, 'resource')

    def _test_empty_pool_backup(self, func):
        # check correct handle exception with empty pool
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_pool(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"}, 'resource')

    def _create_fake_pool_backup(self):
        pool = mock.Mock()
        pool.XMLDesc = mock.Mock(return_value="<pool/>")
        pool.isActive = mock.Mock(return_value=1)
        pool.name = mock.Mock(return_value="pool_name")

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        _ctx.instance.runtime_properties["backups"] = {
            "node_name-backup": "<xml/>"}
        return _ctx, connect, pool

    def test_snapshot_apply(self):
        self._test_no_resource_id(pool_tasks.snapshot_apply,
                                  "No pool for restore")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.snapshot_apply)
        self._test_empty_connection_backup(pool_tasks.snapshot_apply)
        self._test_empty_pool_backup(pool_tasks.snapshot_apply)

        # no such snapshot
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                pool_tasks.snapshot_apply(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)

        # we have such snapshot
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            pool_tasks.snapshot_apply(
                ctx=_ctx, snapshot_name="backup",
                snapshot_incremental=True)

        # no such backup
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
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
                    pool_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # have backup
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "<pool/>"
                with mock.patch(
                    '__builtin__.open', fake_file
                ):
                    pool_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)
                fake_file.assert_called_with('./backup!/resource.xml', 'r')

    def test_snapshot_create(self):
        self._test_no_resource_id(pool_tasks.snapshot_create,
                                  "No pool for backup")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.snapshot_create)
        self._test_empty_connection_backup(pool_tasks.snapshot_create)
        self._test_empty_pool_backup(pool_tasks.snapshot_create)

        # check create snapshot with error, already exists
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Snapshot node_name-backup already exists."
            ):
                pool_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                           snapshot_incremental=True)
        connect.storagePoolLookupByName.assert_called_with('resource')

        # no such snapshots
        _ctx.instance.runtime_properties["backups"] = {}
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            pool_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                       snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {"node_name-backup": "<pool/>"})

        # check create snapshot
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isdir",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "!!!!"
                with mock.patch(
                    '__builtin__.open', fake_file
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
                            pool_tasks.snapshot_create(
                                ctx=_ctx, snapshot_name="backup",
                                snapshot_incremental=False)
                    # without error
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=False)
                    ):
                        pool_tasks.snapshot_create(
                            ctx=_ctx, snapshot_name="backup",
                            snapshot_incremental=False)
                    fake_file().write.assert_called_with("<pool/>")

    def test_snapshot_delete(self):
        self._test_no_resource_id(pool_tasks.snapshot_delete,
                                  "No pool for backup delete")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.snapshot_delete)

        # no such snapshots
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                pool_tasks.snapshot_delete(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {'node_name-backup': "<xml/>"})

        # remove snapshot
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            pool_tasks.snapshot_delete(ctx=_ctx, snapshot_name="backup",
                                       snapshot_incremental=True)
        self.assertEqual(_ctx.instance.runtime_properties["backups"], {})

        # no such backup
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
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
                    pool_tasks.snapshot_delete(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # remove backup
        _ctx, connect, pool = self._create_fake_pool_backup()
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "!!!!"
                with mock.patch(
                    '__builtin__.open', fake_file
                ):
                    remove_mock = mock.Mock()
                    with mock.patch(
                        "os.remove",
                        remove_mock
                    ):
                        pool_tasks.snapshot_delete(
                            ctx=_ctx, snapshot_name="backup!",
                            snapshot_incremental=False)
                    remove_mock.assert_called_with('./backup!/resource.xml')
                fake_file.assert_called_with('./backup!/resource.xml', 'r')

    def test_create(self):
        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.create, [], {'ctx': self._create_ctx()})

        # check error with create pool
        self._check_create_object(
            'Failed to create a virtual pool',
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.create, [], {'ctx': self._create_ctx()})

    def test_reuse_pool_create_not_exist(self):
        # check correct handle exception with empty network
        _ctx = self._create_ctx()
        self._check_no_such_object_pool(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.create, [], {
                'ctx': _ctx,
                "resource_id": 'resource',
                "use_external_resource": True,
            }, 'resource')

    def test_reuse_pool_create_exist(self):
        # check that we can use network
        _ctx = self._create_ctx()

        pool = mock.Mock()
        pool.name = mock.Mock(return_value="resource")

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            pool_tasks.create(ctx=_ctx,
                              resource_id='resource',
                              use_external_resource=True)
        connect.storagePoolLookupByName.assert_called_with('resource')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], 'resource'
        )
        self.assertTrue(
            _ctx.instance.runtime_properties['use_external_resource']
        )

    def test_start(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.start)
        self._test_reused_object(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.start)
        self._test_no_resource_id(pool_tasks.start, "No pool for start")

    def test_configure(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.configure)

        self._test_empty_pool(pool_tasks.configure)
        self._test_reused_object(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.configure)
        self._test_no_resource_id(pool_tasks.configure,
                                  "No pool for configure")

    def test_stop(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.stop)

        self._test_empty_pool(pool_tasks.stop)
        self._test_reused_object(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.stop)
        self._test_no_resource_id(pool_tasks.stop)

    def test_delete(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.delete)

        self._test_empty_pool(pool_tasks.delete)
        self._test_reused_object(
            "cloudify_libvirt.pool_tasks.libvirt.open",
            pool_tasks.delete)
        self._test_no_resource_id(pool_tasks.delete)


if __name__ == '__main__':
    unittest.main()
