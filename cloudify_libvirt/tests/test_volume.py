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

from cloudify_common_sdk._compat import PY2

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.volume_tasks as volume_tasks


class TestVolumeTasks(LibVirtCommonTest):

    def _create_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={
                'libvirt_auth': {'a': 'c'},
                'params': {'pool': 'pool_name'},
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
            "cloudify_libvirt.volume_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"})

    def _test_empty_volume_backup(self, func):
        # check correct handle exception with empty volume
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}
        self._check_no_such_object_volume(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            func, [], {'ctx': _ctx, "snapshot_name": "backup"}, 'resource')

    def _test_empty_volume(self, func):
        # check correct handle exception with empty volume
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}
        self._check_no_such_object_volume(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            func, [], {'ctx': _ctx}, 'resource')

    def _create_fake_volume_backup(self):
        volume = mock.Mock()
        volume.XMLDesc = mock.Mock(return_value="<volume/>")
        volume.isActive = mock.Mock(return_value=1)
        volume.name = mock.Mock(return_value="volume_name")

        pool = mock.Mock()
        pool.XMLDesc = mock.Mock(return_value="<pool/>")
        pool.isActive = mock.Mock(return_value=1)
        pool.name = mock.Mock(return_value="pool_name")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}
        _ctx.node.properties['params'] = {}
        _ctx.instance.runtime_properties["backups"] = {
            "node_name-backup": "<xml/>"}
        return _ctx, connect, pool, volume

    def test_snapshot_apply(self):
        self._test_no_resource_id(volume_tasks.snapshot_apply,
                                  "No volume for restore")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.snapshot_apply)
        self._test_empty_connection_backup(volume_tasks.snapshot_apply)
        self._test_empty_volume_backup(volume_tasks.snapshot_apply)

        # no such snapshot
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                volume_tasks.snapshot_apply(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)

        # we have such snapshot
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.snapshot_apply(
                ctx=_ctx, snapshot_name="backup",
                snapshot_incremental=True)

        # no such backup
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
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
                    volume_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # have backup
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "<volume/>"
                builtins_open = '__builtin__.open' if PY2 else 'builtins.open'
                with mock.patch(
                    builtins_open, fake_file
                ):
                    volume_tasks.snapshot_apply(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)
                fake_file.assert_called_with('./backup!/resource.xml', 'r')

    def test_snapshot_create(self):
        self._test_no_resource_id(volume_tasks.snapshot_create,
                                  "No volume for backup")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.snapshot_create)
        self._test_empty_connection_backup(volume_tasks.snapshot_create)
        self._test_empty_volume_backup(volume_tasks.snapshot_create)

        # check create snapshot with error, already exists
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Snapshot node_name-backup already exists."
            ):
                volume_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                             snapshot_incremental=True)
        connect.storagePoolLookupByName.assert_called_with('pool_name')
        pool.storageVolLookupByName.assert_called_with('resource')

        # no such snapshots
        _ctx.instance.runtime_properties["backups"] = {}
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.snapshot_create(ctx=_ctx, snapshot_name="backup",
                                         snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {"node_name-backup": "<volume/>"})

        # check create snapshot
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isdir",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "!!!!"
                builtins_open = '__builtin__.open' if PY2 else 'builtins.open'
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
                            volume_tasks.snapshot_create(
                                ctx=_ctx, snapshot_name="backup",
                                snapshot_incremental=False)
                    # without error
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=False)
                    ):
                        volume_tasks.snapshot_create(
                            ctx=_ctx, snapshot_name="backup",
                            snapshot_incremental=False)
                    fake_file().write.assert_called_with("<volume/>")

    def test_snapshot_delete(self):
        self._test_no_resource_id(volume_tasks.snapshot_delete,
                                  "No volume for backup delete")
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.snapshot_delete)

        # no such snapshots
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "No snapshots found with name: node_name-backup!."
            ):
                volume_tasks.snapshot_delete(
                    ctx=_ctx, snapshot_name="backup!",
                    snapshot_incremental=True)
        self.assertEqual(
            _ctx.instance.runtime_properties["backups"],
            {'node_name-backup': "<xml/>"})

        # remove snapshot
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.snapshot_delete(ctx=_ctx, snapshot_name="backup",
                                         snapshot_incremental=True)
        self.assertEqual(_ctx.instance.runtime_properties["backups"], {})

        # no such backup
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
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
                    volume_tasks.snapshot_delete(
                        ctx=_ctx, snapshot_name="backup!",
                        snapshot_incremental=False)

        # remove backup
        _ctx, connect, pool, volume = self._create_fake_volume_backup()
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
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
                    _builtins = '__builtin__.open' if PY2 else 'builtins.open'
                    with mock.patch(
                        _builtins, fake_file
                    ):
                        volume_tasks.snapshot_delete(
                            ctx=_ctx, snapshot_name="backup!",
                            snapshot_incremental=False)
                    fake_file.assert_called_with('./backup!/resource.xml', 'r')
                remove_mock.assert_called_with('./backup!/resource.xml')

    def test_create(self):
        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.create, [], {'ctx': self._create_ctx()})

        # check error with create volume image
        self._check_create_object(
            'Failed to find the pool',
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.create, [], {'ctx': self._create_ctx(),
                                      'params': {'pool': 'empty'}})

        # successful create
        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume_name")

        pool = mock.Mock()
        pool.createXML = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)

        # without params
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.create(ctx=_ctx,
                                template_resource="template_resource",
                                params={'pool': 'empty'})
        pool.createXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "volume_name"
        )

        # failed check size of download
        _ctx.instance.runtime_properties['resource_id'] = None
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            # empty
            head_response = mock.Mock()
            head_response.headers = {'Content-Length': 0}
            with mock.patch(
                "cloudify_libvirt.volume_tasks.requests.head",
                mock.Mock(return_value=head_response)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "Failed to download volume."
                ):
                    volume_tasks.create(
                        ctx=_ctx,
                        template_resource="template_resource",
                        params={
                            'pool': 'empty',
                            'url': "https://fake.org/centos.iso"})

        # sucessful check size of download
        _ctx.instance.runtime_properties['resource_id'] = None
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            head_response = mock.Mock()
            head_response.headers = {'Content-Length': 512,
                                     'Accept-Ranges': 'bytes'}
            with mock.patch(
                "cloudify_libvirt.volume_tasks.requests.head",
                mock.Mock(return_value=head_response)
            ):
                volume_tasks.create(
                    ctx=_ctx,
                    template_resource="template_resource",
                    params={
                        'pool': 'empty',
                        'url': "https://fake.org/centos.iso"})

        # failed on create
        _ctx.instance.runtime_properties['resource_id'] = None
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        pool.createXML = mock.Mock(return_value=None)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to create a virtual volume'
            ):
                volume_tasks.create(ctx=_ctx,
                                    template_resource="template_resource",
                                    params={'pool': 'empty'})

    def test_reuse_volume_create_not_exist(self):
        # check correct handle exception with empty network
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}
        self._check_no_such_object_volume(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.create, [], {
                'ctx': _ctx,
                "resource_id": 'resource',
                "use_external_resource": True,
            }, 'resource')

    def test_reuse_volume_create_exist(self):
        # check that we can use network
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume")
        pool = mock.Mock()
        pool.name = mock.Mock(return_value="pool")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()
        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.create(ctx=_ctx,
                                resource_id='resource',
                                use_external_resource=True)
        connect.storagePoolLookupByName.assert_called_with('pool_name')
        pool.storageVolLookupByName.assert_called_with('resource')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], 'volume'
        )
        self.assertTrue(
            _ctx.instance.runtime_properties['use_external_resource']
        )

    def test_start(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.start)

        self._test_empty_volume(volume_tasks.start)
        self._test_reused_object(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.start)
        self._test_no_resource_id(volume_tasks.start)

    def test_start_wipe(self):
        # zero wipe
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'volume'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume")
        volume.upload = mock.Mock()
        pool = mock.Mock()
        pool.name = mock.Mock(return_value="pool")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()

        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.start(ctx=_ctx,
                               params={
                                    'zero_wipe': True,
                                    'allocation': 1
                                })

    def test_start_download(self):
        # download
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'volume'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume")
        volume.upload = mock.Mock()
        pool = mock.Mock()
        pool.name = mock.Mock(return_value="pool")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()

        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            # empty
            head_response = mock.Mock()
            head_response.headers = {'Content-Length': 0}
            with mock.patch(
                "cloudify_libvirt.volume_tasks.requests.head",
                mock.Mock(return_value=head_response)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "Failed to download volume."
                ):
                    volume_tasks.start(
                        ctx=_ctx,
                        params={
                            'url': "https://fake.org/centos.iso"})

            # 512 for download
            head_response = mock.Mock()
            head_response.headers = {'Content-Length': 512,
                                     'Accept-Ranges': 'bytes'}
            head_response.iter_content = mock.Mock(return_value=["\0" * 256])
            with mock.patch(
                "cloudify_libvirt.volume_tasks.requests.head",
                mock.Mock(return_value=head_response)
            ):
                with mock.patch(
                    "cloudify_libvirt.volume_tasks.requests.get",
                    mock.Mock(return_value=head_response)
                ):
                    volume_tasks.start(
                        ctx=_ctx,
                        params={
                            'url': "https://fake.org/centos.iso"})

    def test_stop(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.stop)

        self._test_empty_volume(volume_tasks.stop)
        self._test_reused_object(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.stop)
        self._test_no_resource_id(volume_tasks.stop)

    def test_stop_wipe(self):
        # failed to wipe/error ignored
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'volume'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume")
        volume.wipe = mock.Mock(
            side_effect=volume_tasks.libvirt.libvirtError("e"))
        pool = mock.Mock()
        pool.name = mock.Mock(return_value="pool")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()

        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.stop(ctx=_ctx)
        # failed to wipe/wrong response
        volume.wipe = mock.Mock(return_value=-1)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "cloudify_libvirt.volume_tasks.time.sleep",
                mock.Mock(return_value=mock.Mock())
            ):
                volume_tasks.stop(ctx=_ctx)
        # correctly wiped
        volume.wipe = mock.Mock(return_value=0)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.stop(ctx=_ctx)

    def test_delete(self):
        # check correct handle exception with empty connection
        self._test_check_correct_connect_action(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.delete)

        self._test_empty_volume(volume_tasks.delete)
        self._test_reused_object(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            volume_tasks.delete)
        self._test_no_resource_id(volume_tasks.delete)

        # failed to remove
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'volume'
        _ctx.instance.runtime_properties['params'] = {'pool': 'pool_name'}

        volume = mock.Mock()
        volume.name = mock.Mock(return_value="volume")
        volume.delete = mock.Mock(return_value=-1)
        pool = mock.Mock()
        pool.name = mock.Mock(return_value="pool")
        pool.storageVolLookupByName = mock.Mock(return_value=volume)

        connect = self._create_fake_connection()

        connect.storagePoolLookupByName = mock.Mock(return_value=pool)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Can not undefine volume.'
            ):
                volume_tasks.delete(ctx=_ctx)

        # sucessful remove
        volume.delete = mock.Mock(return_value=0)
        with mock.patch(
            "cloudify_libvirt.volume_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            volume_tasks.delete(ctx=_ctx)
        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                'backups': {},
                'libvirt_auth': {'a': 'd'},
                'params': {},
                'resource_id': None
            }
        )


if __name__ == '__main__':
    unittest.main()
