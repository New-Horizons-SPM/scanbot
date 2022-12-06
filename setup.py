#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

version = '1.0.0'

setup(
    name='scanbot',
    version=version,
    author='Julian Ceddia',
    author_email='jdceddia@gmail.com',
    description='Collection of automated STM and nc-AFM commands compatible with Nanonis V5 SPM Controller',
    long_description=long_description,
    url='https://github.com/New-Horizons-SPM/scanbot',
    project_urls = {
        "Bug Tracker": "https://github.com/New-Horizons-SPM/scanbot/issues"
    },
    license='MIT',
    packages=find_packages(),
    install_requires=['numpy', 'matplotlib','scipy','opencv-python','zulip'],
)
