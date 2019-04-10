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
import unittest
import mock

from cloudify.exceptions import NonRecoverableError
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext


class LibVirtCommonTest(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(LibVirtCommonTest, self).tearDown()

    def _check_correct_connect(self, libvirt_open, func, args, kwargs):
        # check that we correctly raise exception without connection

        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=None)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                "Failed to open connection to the hypervisor"
            ):
                func(*args, **kwargs)

    def _check_no_such_object_network(self, libvirt_open, func, args, kwargs,
                                      resource_id):
        # check that we correctly raise exception without such object

        # no such
        connect = self._create_fake_connection()
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the network'
            ):
                func(*args, **kwargs)

        connect.networkLookupByName.assert_called_with(resource_id)
        connect.lookupByName.assert_not_called()
        connect.storagePoolLookupByName.assert_not_called()

    def _check_no_such_object_pool(self, libvirt_open, func, args, kwargs,
                                   resource_id):
        # check that we correctly raise exception without such object

        # no such
        connect = self._create_fake_connection()
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the pool'
            ):
                func(*args, **kwargs)

        connect.networkLookupByName.assert_not_called()
        connect.lookupByName.assert_not_called()
        connect.storagePoolLookupByName.assert_called_with(resource_id)

    def _check_no_such_object_volume(self, libvirt_open, func, args, kwargs,
                                     resource_id):
        # check that we correctly raise exception without such object
        # no such
        connect = self._create_fake_connection()
        fake_pool = mock.Mock()
        fake_pool.storageVolLookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("storageVolLookupByName"))
        connect.storagePoolLookupByName = mock.Mock(return_value=fake_pool)
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the volume'
            ):
                func(*args, **kwargs)

        connect.networkLookupByName.assert_not_called()
        connect.lookupByName.assert_not_called()
        connect.storagePoolLookupByName.assert_called_with('pool_name')

    def _check_no_such_object_domain(self, libvirt_open, func, args, kwargs,
                                     resource_id):
        # check that we correctly raise exception without such object

        # no such
        connect = self._create_fake_connection()
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the domain'
            ):
                func(*args, **kwargs)

        connect.networkLookupByName.assert_not_called()
        connect.lookupByName.assert_called_with(resource_id)

        # some strange error
        connect = self._create_fake_connection()
        connect.networkLookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("networkLookupByName"))
        connect.lookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("lookupByName"))
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                'Failed to find the domain'
            ):
                func(*args, **kwargs)

        connect.networkLookupByName.assert_not_called()
        connect.lookupByName.assert_called_with(resource_id)
        connect.storagePoolLookupByName.assert_not_called()

    def _check_create_object(self, error_message, libvirt_open, func, args,
                             kwargs):
        connect = self._create_fake_connection()
        with mock.patch(
            libvirt_open,
            mock.Mock(return_value=connect)
        ):
            with self.assertRaisesRegexp(
                NonRecoverableError,
                error_message
            ):
                func(*args, **kwargs)

    def _create_fake_connection(self):
        connect = mock.Mock()
        connect.networkLookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("networkLookupByName"))
        connect.lookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("lookupByName"))
        connect.storagePoolLookupByName = mock.Mock(
            side_effect=libvirt.libvirtError("storagePoolLookupByName"))
        connect.networkCreateXML = mock.Mock(return_value=None)
        connect.defineXML = mock.Mock(return_value=None)
        connect.storagePoolDefineXML = mock.Mock(return_value=None)
        connect.close = mock.Mock(return_value=None)
        connect.newStream = mock.Mock(return_value=mock.Mock())
        return connect

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

    def _test_no_resource_id(self, func, exception_text=None):
        # no initilized/no resource id
        _ctx = self._create_ctx()
        if not exception_text:
            func(ctx=_ctx)
        else:
            with self.assertRaisesRegexp(
                NonRecoverableError,
                exception_text
            ):
                func(ctx=_ctx)

    def _test_reused_object(self, libvirt_open, func, use_existed=True):
        # check use prexisted object
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        _ctx.instance.runtime_properties['use_external_resource'] = use_existed
        connect = self._create_fake_connection()
        with mock.patch(libvirt_open, mock.Mock(return_value=connect)):
            func(ctx=_ctx)

    def _test_no_snapshot_name(self, _ctx, libvirt_open, func):
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        with self.assertRaisesRegexp(
            NonRecoverableError,
            "Backup name must be provided."
        ):
            connect = self._create_fake_connection()
            connect.networkLookupByName = mock.Mock()
            connect.lookupByName = mock.Mock()
            connect.storagePoolLookupByName = mock.Mock()
            with mock.patch(libvirt_open, mock.Mock(return_value=connect)):
                func(ctx=_ctx)

    def _test_check_correct_connect_action(self, libvirt_open, func):
        # check correct handle exception with empty connection
        # for start/stop/delete
        _ctx = self._create_ctx()
        _ctx.instance.runtime_properties['resource_id'] = 'resource'
        self._check_correct_connect(
            libvirt_open,
            func, [], {'ctx': _ctx})
