#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Unless otherwise noted, all files are released under this license,
exceptions contain licensing information in them.

Copyright (C) 2014 Rackspace UK

Permission is hereby granted, free of charge, to any Racker obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject
to the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR
ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name of Rackspace UK.
shall not be used in advertising or otherwise to promote the sale,
use or other dealings in this Software without prior written
authorization from Rackspace UK.
'''

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

from raxas.version import VERSION

setup(
    name='RAX-AutoScaler',
    version=VERSION,
    url='https://github.com/boxidau/rax-autoscaler',
    author='Simon Mirco, Simone Soldateschi, Suraj Thapa',
    author_email='simon.mirco@rackspace.com, simone.soldateschi@rackspace.co.uk, suraj.thapa@rackspace.com',
    description='Rackspace Auto Scale made easy',
    entry_points = {
        "console_scripts": ['autoscale = raxas.autoscale:main']
    },
    platforms='any',
    install_requires=[
        "pyrax==1.9.2",
        "requests==2.4.3",
        "termcolor==1.1.0",
    ],
    packages=find_packages(),
    package_data={'docs': ['*.rst'], 'raxas': ['requirements.txt']},
    #scripts=['raxas'],
    classifiers=['Programming Language :: Python',
                 'Development Status :: Alpha',
                 'Natural Language :: English',
                 'Environment :: Console',
                 'Intended Audience :: DevOps and Cloud Technologists'],
)


