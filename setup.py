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
import sys
from setuptools import setup

PY2 = sys.version_info[0] == 2


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_file='plugin.yaml'):
    lines = read(rel_file)
    for line in lines.splitlines():
        if 'package_version' in line:
            split_line = line.split(':')
            line_no_space = split_line[-1].replace(' ', '')
            line_no_quotes = line_no_space.replace('\'', '')
            return line_no_quotes.strip('\n')
    raise RuntimeError('Unable to find version string.')

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
        'libvirt-python>=4.5.0,<6.0',
        # cdrom create code
        "cloudify-utilities-plugins-sdk==0.0.27",
    ],
)
