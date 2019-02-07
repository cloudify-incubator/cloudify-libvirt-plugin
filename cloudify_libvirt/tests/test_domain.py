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
import libvirt

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.manager import DirtyTrackingDict

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
            runtime_properties=DirtyTrackingDict({
                'params': {'c': "d", 'e': 'g'},
                'libvirt_auth': {'a': 'd'}
            })
        )
        current_ctx.set(_ctx)
        return _ctx

    def test_reuse_domain_create_not_exist(self):
        # check correct handle exception with empty domain
        _ctx = self._create_ctx()
        self._check_no_such_object_domain(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.configure, [], {
                'ctx': _ctx,
                "resource_id": 'resource',
                "use_external_resource": True
            }, 'resource')

    def test_reuse_domain_create_exist(self):
        # check that we can use domain
        _ctx = self._create_ctx()

        domain = mock.Mock()
        domain.name = mock.Mock(return_value="resource")

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.configure(ctx=_ctx, resource_id='resource',
                                   use_external_resource=True)
        connect.lookupByName.assert_called_with('resource')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], 'resource'
        )
        self.assertTrue(
            _ctx.instance.runtime_properties['use_external_resource']
        )

    def test_create(self):
        """check create call, should run get_libvirt_params, without any
        real logic"""
        _ctx = self._create_ctx()

        with mock.patch(
            "cloudify_libvirt.common.uuid.uuid4",
            mock.Mock(return_value="some_uuid")
        ):
            domain_tasks.create(ctx=_ctx, params={'z': 'y'},
                                libvirt_auth={'w': 'x'})
        self.assertEqual(_ctx.instance.runtime_properties, {
            'libvirt_auth': {'w': 'x'},
            'params': {
                # default values
                'name': 'node_name', 'instance_uuid': 'some_uuid',
                # values from inputs
                'a': 'b', 'c': 'd', 'e': 'g', 'z': 'y'
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

        # without params
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.configure(ctx=_ctx,
                                   template_resource="template_resource")
        connect.defineXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_id'], "domain_name"
        )
        # with params from inputs
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.configure(ctx=_ctx,
                                   template_resource="template_resource",
                                   params={"memory_size": 1024})
        connect.defineXML.assert_called_with('<somexml/>')
        self.assertEqual(
            _ctx.instance.runtime_properties['params']['memory_maxsize'],
            2048)
        self.assertEqual(
            _ctx.instance.runtime_properties['params']['memory_size'],
            1024)

    def test_update(self):
        self._test_no_resource_id(domain_tasks.update,
                                  "No servers for update")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.update)
        self._test_check_correct_connect_no_object(domain_tasks.update)
        # check memory
        self._test_action_states(
            domain_tasks.update,
            [libvirt.VIR_DOMAIN_RUNNING],
            'Can not change memory amount.',
            params_update={'memory_size': 1024})
        # check max memory
        self._test_action_states(
            domain_tasks.update,
            [libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            'Can not change max memory amount.',
            params_update={'memory_maxsize': 1024})
        # check cpu
        self._test_action_states(
            domain_tasks.update,
            [libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            'Can not change cpu count.',
            params_update={'vcpu': 1024})

    def test_reboot(self):
        self._test_no_resource_id(domain_tasks.reboot,
                                  "No servers for reboot")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.reboot)
        self._test_check_correct_connect_no_object(domain_tasks.reboot)
        self._test_action_states(
            domain_tasks.reboot,
            [],
            'Can not reboot guest domain.')

    def test_start(self):
        self._test_no_resource_id(domain_tasks.start,
                                  "No servers for start")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.start)
        self._test_check_correct_connect_no_object(domain_tasks.start)
        self._test_action_states(
            domain_tasks.start,
            [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            'Can not start guest domain.', 'No ip for now, try later')

    def test_stop(self):
        self._test_no_resource_id(domain_tasks.stop)
        self._test_reused_object(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.stop)
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.stop)
        self._test_check_correct_connect_no_object(domain_tasks.stop)
        self._test_action_states(
            domain_tasks.stop,
            [libvirt.VIR_DOMAIN_RUNNING_UNKNOWN, libvirt.VIR_DOMAIN_RUNNING],
            'Can not shutdown guest domain.')

    def test_resume(self):
        self._test_no_resource_id(domain_tasks.resume,
                                  "No servers for resume")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.resume)
        self._test_check_correct_connect_no_object(domain_tasks.resume)
        self._test_action_states(
            domain_tasks.resume,
            [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_RUNNING_UNKNOWN],
            "Can not suspend guest domain.")

    def test_suspend(self):
        self._test_no_resource_id(domain_tasks.suspend,
                                  "No servers for suspend")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.suspend)
        self._test_check_correct_connect_no_object(domain_tasks.suspend)
        self._test_action_states(
            domain_tasks.suspend,
            [libvirt.VIR_DOMAIN_RUNNING_UNPAUSED, libvirt.VIR_DOMAIN_RUNNING],
            "Can not suspend guest domain.")

    def test_delete(self):
        self._test_no_resource_id(domain_tasks.delete)
        self._test_reused_object(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.delete)
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.delete)
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
                "Still have several snapshots: \\['snapshot!'\\]."
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
        self._test_no_resource_id(domain_tasks.perfomance,
                                  "No servers for statistics.")
        self._test_check_correct_connect_action(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            domain_tasks.perfomance)
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

    def test_update_network_list(self):
        _ctx = self._create_ctx()
        domain = mock.Mock()
        domain.name = mock.Mock(return_value="domain_name")

        # info from leases
        _ctx.instance.runtime_properties['ip'] = '127.0.0.1'
        domain.interfaceAddresses = mock.Mock(return_value={})
        domain_tasks._update_network_list(domain)
        domain.interfaceAddresses.assert_called_with(
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)

        # info from agent
        _ctx.instance.runtime_properties['ip'] = None
        domain.interfaceAddresses = mock.Mock(return_value={})
        domain_tasks._update_network_list(domain, False)
        domain.interfaceAddresses.assert_called_with(
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT)

        # insert new
        _ctx.instance._runtime_properties = DirtyTrackingDict({})
        domain.interfaceAddresses = mock.Mock(return_value={
            'vnet0': {
                'hwaddr': '52:54:00:09:ba:97',
                'addrs': [{
                    'prefix': 24,
                    'type': 0,
                    'addr': '192.168.142.148'
                }]
            }
        })
        domain_tasks._update_network_list(domain, True)
        self.assertEqual(
            _ctx.instance.runtime_properties['params']["networks"],
            [{
                'addrs': [{
                    'prefix': 24,
                    'addr': '192.168.142.148',
                    'type': 0
                }],
                'mac': '52:54:00:09:ba:97',
                'dev': 'vnet0'
            }]
        )

        # update
        _ctx.instance.runtime_properties['params']["networks"] = [{
            'network': 'common_network',
            'dev': 'vnet0',
            'mac': '52:54:00:09:ba:97'
        }]
        domain.interfaceAddresses = mock.Mock(return_value={
            'vnet0': {
                'hwaddr': '52:54:00:09:ba:97',
                'addrs': [{
                    'prefix': 24,
                    'type': 0,
                    'addr': '192.168.142.149'
                }]
            }
        })
        domain_tasks._update_network_list(domain, True)
        self.assertEqual(
            _ctx.instance.runtime_properties['params']["networks"],
            [{
                'network': 'common_network',
                'mac': '52:54:00:09:ba:97',
                'dev': 'vnet0',
                'addrs': [{
                    'prefix': 24,
                    'type': 0,
                    'addr': '192.168.142.149'
                }],
            }]
        )

    def _test_action_states(self, func, states, error_text,
                            error_check_ip=None, params_update=None):
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'check'
        _ctx.instance.runtime_properties['params']['wait_for_ip'] = True
        if params_update:
            _ctx.instance.runtime_properties['params'].update(params_update)
        fake_states = [state for state in states]

        def _fake_state():
            return fake_states.pop(), ""

        domain = mock.Mock()
        domain.name = mock.Mock(return_value="domain_name")
        domain.interfaceAddresses = mock.Mock(return_value={})
        domain.state = _fake_state

        connect = self._create_fake_connection()
        connect.lookupByName = mock.Mock(return_value=domain)

        # can't run
        domain.create = mock.Mock(return_value=-1)
        domain.shutdown = mock.Mock(return_value=-1)
        domain.resume = mock.Mock(return_value=-1)
        domain.suspend = mock.Mock(return_value=-1)
        domain.reboot = mock.Mock(return_value=-1)
        domain.setMemory = mock.Mock(return_value=-1)
        domain.setMaxMemory = mock.Mock(return_value=-1)
        domain.setVcpus = mock.Mock(return_value=-1)

        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                error_text
            ):
                func(ctx=_ctx)

        _ctx.instance.runtime_properties['params']['wait_for_ip'] = False
        # run
        domain.create = mock.Mock(return_value=0)
        domain.shutdown = mock.Mock(return_value=0)
        domain.resume = mock.Mock(return_value=0)
        domain.suspend = mock.Mock(return_value=0)
        domain.reboot = mock.Mock(return_value=0)
        domain.setMemory = mock.Mock(return_value=0)
        domain.setMaxMemory = mock.Mock(return_value=0)
        domain.setVcpus = mock.Mock(return_value=0)
        fake_states = [state for state in states]

        def _fake_state():
            return fake_states.pop(), ""

        domain.state = _fake_state
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

        # no ip but running
        if error_check_ip:
            domain.state = mock.Mock(
                return_value=(libvirt.VIR_DOMAIN_RUNNING, ""))
            _ctx.instance.runtime_properties['params']['wait_for_ip'] = True
            with mock.patch(
                "cloudify_libvirt.domain_tasks.libvirt.open",
                mock.Mock(return_value=connect)
            ):
                with self.assertRaisesRegexp(
                    RecoverableError,
                    error_check_ip
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

    def _check_create_backups(self, _ctx, connect, domain, snapshot, raw_case):
        # raw_case - dump xml without real raw dump
        _ctx.instance.runtime_properties['params']['full_dump'] = raw_case

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
                "Snapshot snapshot\\! already exists."
            ):
                domain_tasks.snapshot_create(
                    ctx=_ctx,
                    template_resource="template_resource",
                    snapshot_name='snapshot_name',
                    snapshot_incremental=True)

        # check create snapshot
        domain.XMLDesc = mock.Mock(return_value="<domain/>")
        domain.save = mock.Mock()
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isdir",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                if not raw_case:
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
                            "Backup node_name-snapshot_name already exists."
                        ):
                            domain_tasks.snapshot_create(
                                ctx=_ctx,
                                template_resource="template_resource",
                                snapshot_name='snapshot_name',
                                snapshot_incremental=False)
                    # without error
                    with mock.patch(
                        "os.path.isfile",
                        mock.Mock(return_value=False)
                    ):
                        domain_tasks.snapshot_create(
                            ctx=_ctx, template_resource="template_resource",
                            snapshot_name='snapshot_name',
                            snapshot_incremental=False)
                if raw_case:
                    fake_file.assert_not_called()
                    domain.save.assert_called_with(
                        './snapshot_name/check_raw')
                    connect.restore.assert_called_with(
                        './snapshot_name/check_raw')
                else:
                    fake_file().write.assert_called_with("<domain/>")

    def test_snapshot_create(self):
        self._test_common_backups(domain_tasks.snapshot_create,
                                  "No servers for backup.")

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
        connect.restore = mock.Mock()
        _ctx.instance.runtime_properties['params'] = {}
        _ctx.node.properties['params'] = {}
        _ctx.instance.runtime_properties['resource_id'] = 'check'

        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_create(ctx=_ctx,
                                         template_resource="template_resource",
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

        # raw dump
        self._check_create_backups(_ctx, connect, domain, snapshot, True)

        # check fast backup
        self._check_create_backups(_ctx, connect, domain, snapshot, False)

    def _check_apply_backups(self, _ctx, connect, domain, raw_case):
        # raw_case - dump xml without real raw dump
        _ctx.instance.runtime_properties['params']['full_dump'] = raw_case

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
                    "No backups found with name: node_name-snapshot_name."
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
                if not raw_case:
                    fake_file().read.return_value = "old"
                with mock.patch(
                    '__builtin__.open', fake_file
                ):
                    # have same backup
                    domain.snapshotNum = mock.Mock(return_value=0)
                    domain.state = mock.Mock(
                        return_value=(libvirt.VIR_DOMAIN_SHUTOFF, ""))
                    domain.XMLDesc = mock.Mock(return_value="old")
                    domain_tasks.snapshot_apply(ctx=_ctx,
                                                snapshot_name='snapshot_name',
                                                snapshot_incremental=False)
                    # have different backup
                    domain.XMLDesc = mock.Mock(return_value="new")
                    domain_tasks.snapshot_apply(ctx=_ctx,
                                                snapshot_name='snapshot_name',
                                                snapshot_incremental=False)
                if raw_case:
                    fake_file.assert_not_called()
                    connect.restore.assert_called_with(
                        './snapshot_name/resource_raw')
                else:
                    fake_file.assert_called_with(
                        './snapshot_name/resource.xml', "r")

    def test_snapshot_apply(self):
        self._test_common_backups(domain_tasks.snapshot_apply,
                                  "No servers for restore.")

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
        connect.restore = mock.Mock()
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            domain_tasks.snapshot_apply(ctx=_ctx,
                                        snapshot_name='snapshot_name',
                                        snapshot_incremental=True)
        domain.revertToSnapshot.assert_called_with(snapshot)

        # raw dump
        self._check_apply_backups(_ctx, connect, domain, True)

        # check fast backup
        self._check_apply_backups(_ctx, connect, domain, False)

    def _check_delete_backups(self, _ctx, connect, raw_case):
        # raw_case - dump xml without real raw dump
        _ctx.instance.runtime_properties['params']['full_dump'] = raw_case

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
                    "No backups found with name: node_name-snapshot_name."
                ):
                    domain_tasks.snapshot_delete(ctx=_ctx,
                                                 snapshot_name='snapshot_name',
                                                 snapshot_incremental=False)

        # have some backups
        with mock.patch(
            "cloudify_libvirt.domain_tasks.libvirt.open",
            mock.Mock(return_value=connect)
        ):
            with mock.patch(
                "os.path.isfile",
                mock.Mock(return_value=True)
            ):
                fake_file = mock.mock_open()
                if not raw_case:
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
                    if raw_case:
                        remove_mock.assert_called_with(
                            './snapshot_name/resource_raw')
                        fake_file.assert_not_called()
                    else:
                        remove_mock.assert_called_with(
                            './snapshot_name/resource.xml')

    def test_snapshot_delete(self):
        self._test_common_backups(domain_tasks.snapshot_delete,
                                  "No servers for remove_backup.")

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
                "Sub snapshots \\['snapshot-'\\] found for "
                "node_name-snapshot_name. You should remove subsnaphots before"
                " remove current."
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

        # raw dump
        self._check_delete_backups(_ctx, connect, True)

        # check fast backup
        self._check_delete_backups(_ctx, connect, False)

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

    def _test_common_backups(self, func, noresource_text):
        # common funcs for backups
        self._test_no_resource_id(func, noresource_text)
        self._test_no_snapshot_name(
            self._create_ctx(),
            "cloudify_libvirt.domain_tasks.libvirt.open",
            func)
        self._test_snapshot_name_backup(func)
        self._test_check_correct_connect_backup(func)
        self._test_check_correct_connect_backup_no_object(func)


if __name__ == '__main__':
    unittest.main()
