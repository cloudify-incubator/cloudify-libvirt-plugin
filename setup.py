# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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
from setuptools import setup

setup(
    name='cloudify-libvirt-plugin',
    version='0.6.0',
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
        ]
    },
    install_requires=[
        'cloudify-plugins-common>=3.3',
        'libvirt-python',
        "Jinja2>=2.7.2",  # for template support
    ],
)
