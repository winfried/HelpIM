#!/usr/bin/env python

import sys, os
from setuptools import setup, find_packages
from os.path import join, dirname, relpath
from version import get_git_version

sys.path.append(join(dirname(__file__), 'helpim'))

long_description=(
    open(join(dirname(__file__),
         'README.rst',
         )).read())

name='helpim'

install_requires=[
   'setuptools',
   'distribute==0.6.16',
   'setuptools==0.6c11',
   'django>=1.3',
   'mysql-python==1.2.3',
   'south==0.7.3',
   'django-threadedcomments==0.5.3',
   'django-rosetta==0.6.0',
   'pyxmpp==1.1.1',
   'libxml2-python==2.6.21',
   ]

include_dirs = [
    'static',
    'helpim/locale',
    'helpim/templates',
    'helpim/fixtures',
    'helpim/questionnaire/templates/forms',
    'helpim/doc/debian/example',
    ]

static_files = []
for include_dir in include_dirs:
    for root, dirs, files in os.walk(join(dirname(__file__), include_dir)):
        relroot = relpath(root, dirname(__file__))
        static_files.append((
          join('share', 'helpim', relroot),
          [join(relroot, f) for f in files]
        ))

setup(
    name=name,
    version=get_git_version().lstrip('v'),
    url='http://www.python.org/pypi/'+name,
    license='AGPL',
    description='A chat-system for online psycho-social counselling',
    long_description=long_description,
    author='e-hulp.nl HelpIM Team',
    author_email='helpdesk@e-hulp.nl',
    packages=find_packages('.'),
    package_dir={'': '.'},
    data_files=static_files,
    namespace_packages=[],
    include_package_data = True,
    install_requires=install_requires,
    zip_safe = False,
    classifiers = [
      "Programming Language :: Python",
      "Development Status :: 4 - Beta",
      "Environment :: Other Environment",
    ],
    extras_require = dict(
        test=[],
        ),
    entry_points = dict(
        console_scripts=[],
        ),
    )
