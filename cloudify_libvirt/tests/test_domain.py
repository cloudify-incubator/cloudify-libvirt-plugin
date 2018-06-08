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
import unittest
import libvirt

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError

from cloudify_libvirt.tests.test_common_base import LibVirtCommonTest
import cloudify_libvirt.domain_tasks as domain_tasks


class TestDomainTasks(LibVirtCommonTest):

    def _create_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={
                'params': {'a': "b", 'c': 'g'},
                'libvirt_auth': {'a': 'c'}
            },
            runtime_properties={
                'params': {'c': "d", 'e': 'g', 'memory_size': 1024},
                'libvirt_auth': {'a': 'd'}
            }
        )
        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        """check create call, should run get_libvirt_params, without any
        real logic"""
        _ctx = self._create_ctx()

        domain_tasks.create(ctx=_ctx, params={'z': 'y'},
                            libvirt_auth={'w': 'x'})
        self.assertEqual(_ctx.instance.runtime_properties, {
            'libvirt_auth': {'w': 'x'},
            'params': {
                'a': 'b', 'c': 'd', 'e': 'g', 'z': 'y', 'memory_size': 1024
            }
        })

    def test_configure(self):
        _ctx = self._create_ctx()

        # check correct handle exception with empty connection
        self._check_correct_connect(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.configure, [], {'ctx': _ctx})

        # check error with create domain
        _ctx = self._create_ctx()
        self._check_create_object(
            'Failed to define a domain from an XML definition.',
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.configure, [], {'ctx': _ctx})

        # check with without params and custom file
        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')

        domain = mock.Mock()
        domain.name = mock.Mock(return_value="domain_name")

        connect = self._create_fake_connection()
        connect.defineXML = mock.Mock(return_value=domain)
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.configure(ctx=_ctx, domain_file="domain_file")
        connect.defineXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "domain_name"
        )

    def test_start(self):
        self._test_no_resource_id(domain_tasks.start)
        self._test_check_correct_connect_action(domain_tasks.start)
        self._test_check_correct_connect_no_object(domain_tasks.start)
        self._test_action_states(
            domain_tasks.start,
            [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            'Can not start guest domain.')

    def test_stop(self):
        self._test_no_resource_id(domain_tasks.stop)
        self._test_check_correct_connect_action(domain_tasks.stop)
        self._test_check_correct_connect_no_object(domain_tasks.stop)
        self._test_action_states(
            domain_tasks.stop,
            [libvirt.VIR_DOMAIN_RUNNING_UNKNOWN, libvirt.VIR_DOMAIN_RUNNING],
            'Can not shutdown guest domain.')

    def test_resume(self):
        self._test_no_resource_id(domain_tasks.resume)
        self._test_check_correct_connect_action(domain_tasks.resume)
        self._test_check_correct_connect_no_object(domain_tasks.resume)
        self._test_action_states(
            domain_tasks.resume,
            [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            "Can not suspend guest domain.")

    def test_suspend(self):
        self._test_no_resource_id(domain_tasks.suspend)
        self._test_check_correct_connect_action(domain_tasks.suspend)
        self._test_check_correct_connect_no_object(domain_tasks.suspend)
        self._test_action_states(
            domain_tasks.suspend,
            [libvirt.VIR_DOMAIN_RUNNING_UNPAUSED, libvirt.VIR_DOMAIN_RUNNING],
            "Can not suspend guest domain.")

    def test_delete(self):
        self._test_no_resource_id(domain_tasks.delete)
        self._test_check_correct_connect_action(domain_tasks.delete)
        self._test_check_correct_connect_no_object(domain_tasks.delete)

        # delete snapshot with error
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        snapshot = mock.Mock()
        snapshot.delete = mock.Mock()
        snapshot.getName = mock.Mock(return_value="snapshot!")
        snapshot.numChildren = mock.Mock(return_value=0)
        snapshot.listAllChildren = mock.Mock(return_value=[])
        domain = mock.Mock()
        domain.revertToSnapshot = mock.Mock()
        domain.snapshotNum = mock.Mock(return_value=1)
        domain.listAllSnapshots = mock.Mock(
            return_value=[snapshot]
        )
        domain.name = mock.Mock(return_value="domain_name")

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                RecoverableError,
                "Still have several snapshots: \['snapshot!'\]."
            ):
                domain_tasks.delete(ctx=_ctx,
                                    snapshot_name='snapshot_name',
                                    snapshot_incremental=True)

            # removed snaphsots, can't stop
            list_snapshots_results = [[], [snapshot]]

            def _snapshot_list():
                return list_snapshots_results.pop()

            domain.listAllSnapshots = _snapshot_list
            domain.destroy = mock.Mock(return_value=-1)
            domain.state = mock.Mock(
                return_value=(libvirt.VIR_DOMAIN_RUNNING, ""))

            with self.assertRaisesRegexp(
                RecoverableError,
                'Can not destroy guest domain.'
            ):
                domain_tasks.delete(ctx=_ctx,
                                    snapshot_name='snapshot_name',
                                    snapshot_incremental=True)

            # can't undefineFlags
            domain.state = mock.Mock(
                return_value=(libvirt.VIR_DOMAIN_RUNNING, ""))
            domain.destroy = mock.Mock(return_value=0)
            domain.listAllSnapshots = mock.Mock(return_value=[])
            domain.snapshotNum = mock.Mock(return_value=0)
            domain.undefineFlags = mock.Mock(return_value=-1)
            with self.assertRaisesRegexp(
                RecoverableError,
                'Can not undefine guest domain with NVRAM.'
            ):
                domain_tasks.delete(ctx=_ctx,
                                    snapshot_name='snapshot_name',
                                    snapshot_incremental=True)
            # use undefine
            domain.undefineFlags = mock.Mock(
                side_effect=AttributeError("e"))
            domain.undefine = mock.Mock(return_value=-1)
            with self.assertRaisesRegexp(
                RecoverableError,
                'Can not undefine guest domain.'
            ):
                domain_tasks.delete(ctx=_ctx,
                                    snapshot_name='snapshot_name',
                                    snapshot_incremental=True)

            # use undefine
            domain.undefineFlags = mock.Mock(return_value=0)
            domain.undefine = mock.Mock(return_value=0)

            domain_tasks.delete(ctx=_ctx,
                                snapshot_name='snapshot_name',
                                snapshot_incremental=True)
            self.assertFalse(
                _ctx.instance.runtime_properties.get('resource_id'))

    def test_perfomance(self):
        self._test_no_resource_id(domain_tasks.perfomance)
        self._test_check_correct_connect_action(domain_tasks.perfomance)
        self._test_check_correct_connect_no_object(domain_tasks.perfomance)

        # some fake statistics
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'check'
        fake_stats = [[{'system_time': 1000000000.0}], {}]

        def _fake_getCPUStats(check):
            return fake_stats.pop()

        domain = mock.Mock()
        domain.name = mock.Mock(return_value="domain_name")

        domain.getCPUStats = _fake_getCPUStats
        domain.memoryStats = mock.Mock(return_value={'actual': 1024})

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)

        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "time.sleep",
                mock.Mock(return_value=None)
            ):
                domain_tasks.perfomance(ctx=_ctx)

        self.assertEqual(
            _ctx.instance.runtime_properties['stat'],
            {'cpu': 20.0, 'memory': 1.0}
        )

    def _test_action_states(self, func, states, error_text):
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'check'
        fake_states = [state for state in states]

        def _fake_state():
            return fake_states.pop(), ""

        domain = mock.Mock()
        domain.name = mock.Mock(return_value="domain_name")
        domain.state = _fake_state

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)

        # can't run
        domain.create = mock.Mock(return_value=-1)
        domain.shutdown = mock.Mock(return_value=-1)
        domain.resume = mock.Mock(return_value=-1)
        domain.suspend = mock.Mock(return_value=-1)

        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                error_text
            ):
                func(ctx=_ctx)

        # run
        domain.create = mock.Mock(return_value=0)
        domain.shutdown = mock.Mock(return_value=0)
        domain.resume = mock.Mock(return_value=0)
        domain.suspend = mock.Mock(return_value=0)
        fake_states = [state for state in states]

        def _fake_state():
            return fake_states.pop(), ""

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "time.sleep",
                mock.Mock(return_value=None)
            ):
                func(ctx=_ctx)

    def _test_check_correct_connect_no_object(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_domain(
            "cloudify_libvirt.domain_tasks.libvirt.open", func, [],
            {'ctx': _ctx}, 'resource')

    def _test_check_correct_connect_action(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            func, [], {'ctx': _ctx})

    def test_snapshot_create(self):
        self._test_common_backups(domain_tasks.snapshot_create)

        # check with without params and custom file
        _ctx = self._create_ctx()
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')

        snapshot = mock.Mock()
        snapshot.getName = mock.Mock(return_value="snapshot!")
        domain = mock.Mock()
        domain.snapshotLookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("e")
        )
        domain.name = mock.Mock(return_value="domain_name")
        domain.snapshotCreateXML = mock.Mock(return_value=snapshot)

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        _ctx.instance.runtime_properties['resource_id'] = 'check'

        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_create(ctx=_ctx, backup_file="domain_file",
                                         snapshot_name='snapshot_name',
                                         snapshot_incremental=True)
        domain.snapshotCreateXML.assert_called_with('<somexml/>')
        connect.lookupByName.assert_called_with('check')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], 'check'
        )

        # different templates
        _ctx.get_resource = mock.Mock(return_value=None)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_create(ctx=_ctx,
                                         snapshot_name='snapshot_name',
                                         snapshot_incremental=True)

        # already have such
        domain.snapshotLookupByName = mock.Mock(
            return_value=snapshot
        )
        _ctx.get_resource = mock.Mock(return_value='<somexml/>')
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Snapshot snapshot\! already exists."
            ):
                domain_tasks.snapshot_create(ctx=_ctx,
                                             backup_file="domain_file",
                                             snapshot_name='snapshot_name',
                                             snapshot_incremental=True)

        # check create snapshot
        domain.XMLDesc = mock.Mock(return_value="<domain/>")
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
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
                            "Backup snapshot_name already exists."
                        ):
                            domain_tasks.snapshot_create(
                                ctx=_ctx, backup_file="domain_file",
                                snapshot_name='snapshot_name',
                                snapshot_incremental=False)
                    # without error
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=False)
                    ):
                        domain_tasks.snapshot_create(
                            ctx=_ctx, backup_file="domain_file",
                            snapshot_name='snapshot_name',
                            snapshot_incremental=False)
                        fake_file().write.assert_called_with("<domain/>")

    def test_snapshot_apply(self):
        self._test_common_backups(domain_tasks.snapshot_apply)

        # apply snapshot
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        snapshot = mock.Mock()
        snapshot.getName = mock.Mock(return_value="snapshot!")
        domain = mock.Mock()
        domain.revertToSnapshot = mock.Mock()
        domain.snapshotLookupByName = mock.Mock(
            return_value=snapshot
        )
        domain.name = mock.Mock(return_value="domain_name")
        domain.snapshotCreateXML = mock.Mock(
            side_effect=libvirt.libvirtError("e")
        )

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_apply(ctx=_ctx,
                                        snapshot_name='snapshot_name',
                                        snapshot_incremental=True)
        domain.revertToSnapshot.assert_called_with(snapshot)

        # no such backups
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=False)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "No backups found with name: snapshot_name."
                ):
                    domain_tasks.snapshot_apply(ctx=_ctx,
                                                snapshot_name='snapshot_name',
                                                snapshot_incremental=False)
        # have some backup
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                fake_file().read.return_value = "old"
                with mock.patch(
                    '__builtin__.open', fake_file
                ):
                    # have same backup
                    domain.XMLDesc = mock.Mock(return_value="old")
                    domain_tasks.snapshot_apply(ctx=_ctx,
                                                snapshot_name='snapshot_name',
                                                snapshot_incremental=False)
                    # have different backup
                    domain.XMLDesc = mock.Mock(return_value="new")
                    domain_tasks.snapshot_apply(ctx=_ctx,
                                                snapshot_name='snapshot_name',
                                                snapshot_incremental=False)
                fake_file.assert_called_with(
                    './snapshot_name/resource.xml', "r")

    def test_snapshot_delete(self):
        self._test_common_backups(domain_tasks.snapshot_delete)

        # delete snapshot with error
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        sub_snaphot = mock.Mock()
        sub_snaphot.getName = mock.Mock(return_value="snapshot-")

        snapshot = mock.Mock()
        snapshot.delete = mock.Mock()
        snapshot.getName = mock.Mock(return_value="snapshot!")
        snapshot.numChildren = mock.Mock(return_value=1)
        snapshot.listAllChildren = mock.Mock(return_value=[sub_snaphot])
        domain = mock.Mock()
        domain.revertToSnapshot = mock.Mock()
        domain.snapshotLookupByName = mock.Mock(
            return_value=snapshot
        )
        domain.name = mock.Mock(return_value="domain_name")
        domain.snapshotCreateXML = mock.Mock(
            side_effect=libvirt.libvirtError("e")
        )

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Sub snapshots \['snapshot-'\] found for snapshot_name."
                " You should remove subsnaphots before remove current."
            ):
                domain_tasks.snapshot_delete(ctx=_ctx,
                                             snapshot_name='snapshot_name',
                                             snapshot_incremental=True)

        # remove without errors
        snapshot.numChildren = mock.Mock(return_value=0)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_delete(ctx=_ctx,
                                         snapshot_name='snapshot_name',
                                         snapshot_incremental=True)
        snapshot.delete.assert_called_with()

        # no such backups
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=False)
            ):
                with self.assertRaisesRegexp(
                    NonRecoverableError,
                    "No backups found with name: snapshot_name."
                ):
                    domain_tasks.snapshot_delete(ctx=_ctx,
                                                 snapshot_name='snapshot_name',
                                                 snapshot_incremental=False)

        # remove backup
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
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
                        domain_tasks.snapshot_delete(
                            ctx=_ctx, snapshot_name='snapshot_name',
                            snapshot_incremental=False)
                    remove_mock.assert_called_with(
                        './snapshot_name/resource.xml')

    def _test_snapshot_name_backup(self, func):
        # test backup code
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_domain(
            "cloudify_libvirt.domain_tasks.libvirt.open", func, [],
            {'ctx': _ctx, 'snapshot_name': 'snapshot_name',
             'snapshot_incremental': False}, 'resource')

    def _test_check_correct_connect_backup(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            "cloudify_libvirt.domain_tasks.libvirt.open", func, [],
            {'ctx': _ctx, 'snapshot_name': 'snapshot_name',
             'snapshot_incremental': True})

    def _test_check_correct_connect_backup_no_object(self, func):
        # check correct handle exception with empty connection
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_no_such_object_domain(
            "cloudify_libvirt.domain_tasks.libvirt.open", func, [],
            {'ctx': _ctx, 'snapshot_name': 'snapshot_name',
             'snapshot_incremental': True}, 'resource')

    def _test_common_backups(self, func):
        # common funcs for backups
        self._test_no_resource_id(func)
        self._test_no_snapshot_name(self._create_ctx(), func)
        self._test_snapshot_name_backup(func)
        self._test_check_correct_connect_backup(func)
        self._test_check_correct_connect_backup_no_object(func)


if __name__ == '__main__':
    unittest.main()
