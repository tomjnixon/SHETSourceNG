#!/usr/bin/env python

from setuptools import setup

setup(
    name='shetsourceng',
    version='0.1',
    description='Next generation SHETSource router.',
    author='Tom Nixon',
    url='https://github.com/tomjnixon/SHETSourceNG',
    package_dir=dict(shetsourceng="src"),
    packages=["shetsourceng"],
    install_requires=["twisted", "SHET", "mock"],
    scripts=['bin/shetsource_tcp', 'bin/shetsource_direct'])
