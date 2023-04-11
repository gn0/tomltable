#!/usr/bin/env python
# coding: utf8

from setuptools import setup

setup(
    name='tomltable',
    version='1.0',
    description=u'command-line tool to generate TOML-defined regression tables from JSON data files',
    author=u'Gabor Nyeki',
    url='http://www.gabornyeki.com/',
    packages=['tomltable'],
    install_requires=['click', 'toml'],
    provides=['tomltable (1.0)'],
    entry_points={
        'console_scripts': [
            'tomltable = tomltable.tomltable:main',
        ],
    }
    )
