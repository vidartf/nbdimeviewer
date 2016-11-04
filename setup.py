#-----------------------------------------------------------------------------
#  Copyright (C) 2016 The Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import sys
pjoin = os.path.join

from setuptools import setup


setup_args = dict(
    name = "nbviewer",
    version = '0.1.0',
    packages = ["nbdimeviewer"],
    install_requires = [
        'requests>=2.11',
        'pycurl',
        'elasticsearch',
        'newrelic'
    ],
    extras_requires = {
        'memcache': ['pylibmc'],
    },
    author = "The Jupyter Development Team",
    description = "Jupyter Notebook Diff Viewer",
    long_description = "Jupyter nbdime as a web service",
    license = "BSD",
    classifiers = [
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    test_suite="py.test",
)

setup(**setup_args)
