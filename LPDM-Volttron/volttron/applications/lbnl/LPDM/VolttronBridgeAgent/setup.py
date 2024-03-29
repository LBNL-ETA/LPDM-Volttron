# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright (c) 2017, IIIT-Hyderabad
# All rights reserved.
#
#
# IIIT Hyderabad

#}}}

#Sam

from setuptools import setup, find_packages

packages = find_packages('.')
package = packages[0]

setup(
    name = package + 'agent',
    version = "0.1",
    install_requires = ['volttron'],
    packages = packages,
    package_data = {'archiver': ['config.json']},
    entry_points = {
        'setuptools.installation': [
            'eggsecutable = ' + package + '.agent:main',
        ]
    }
)

