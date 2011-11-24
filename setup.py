#!/usr/bin/env python

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
