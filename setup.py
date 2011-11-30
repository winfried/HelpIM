#!/usr/bin/env python

from os import walk
from os.path import join
from setuptools import setup, find_packages
from version import get_git_version

long_description=(open('README.rst').read())

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
    ('/usr/local/share/helpim/static', 'static'),
    ('/usr/local/share/helpim/locale', 'helpim/locale'),
    ('/usr/local/share/helpim/templates', 'helpim/templates'),
    ('/usr/local/share/helpim/templates/forms', 'helpim/questionnaire/templates/forms'),
    ('/usr/local/share/helpim/fixtures', 'helpim/fixtures'),
    ('/usr/local/share/helpim/doc/debian/example', 'helpim/doc/debian/example'),
    ]

static_files = []
for target, include_dir in include_dirs:
    for root, dirs, files in walk(include_dir):
        static_files.append((
          join(target, root[len(include_dir)+1:]),
          [join(root, f) for f in files]
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
    install_requires=install_requires,
    zip_safe = False,
    namespace_packages=[],
    data_files=static_files,
    include_package_data = True,
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
