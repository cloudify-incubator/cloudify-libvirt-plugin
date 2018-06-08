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
        connect.networkLookupByName = mock.Mock(side_effect=OSError("e"))
        connect.lookupByName = mock.Mock(side_effect=OSError("e"))
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
        connect.networkLookupByName = mock.Mock(return_value=None)
        connect.lookupByName = mock.Mock(return_value=None)
        connect.networkCreateXML = mock.Mock(return_value=None)
        connect.defineXML = mock.Mock(return_value=None)
        connect.close = mock.Mock(return_value=None)
        return connect

    def _test_no_resource_id(self, func):
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

        # no initilized/no resource id
        func(ctx=_ctx)

    def _test_no_snapshot_name(self, _ctx, func):
        _ctx.instance.runtime_properties['resource_id'] = 'resource'

        with self.assertRaisesRegexp(
            NonRecoverableError,
            "Backup name must be provided."
        ):
            func(ctx=_ctx)
