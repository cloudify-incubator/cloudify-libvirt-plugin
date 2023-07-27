# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import pathlib
from setuptools import setup


def get_version():
    current_dir = pathlib.Path(__file__).parent.resolve()

    with open(os.path.join(current_dir, 'cloudify_libvirt/__version__.py'),
              'r') as outfile:
        var = outfile.read()
        return re.search(r'\d+.\d+.\d+', var).group()


setup(
    name='cloudify-libvirt-plugin',
    version=get_version(),
    description='support libvirt',
    author='Cloudify',
    author_email='hello@getcloudify.org',
    license='LICENSE',
    packages=['cloudify_libvirt'],
    package_data={
        'cloudify_libvirt': [
            'templates/domain.xml',
            'templates/network.xml',
            'templates/snapshot.xml',
            'templates/pool.xml',
            'templates/volume.xml',
        ]
    },
    install_requires=[
        'cloudify-common>=4.5.0',
        # libvirt-6.0 requires python3
        'libvirt-python==8.5.0',
        # cdrom create code
        "cloudify-utilities-plugins-sdk>=0.0.27",
    ],
)
