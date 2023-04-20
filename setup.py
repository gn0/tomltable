#!/usr/bin/env python
# coding: utf8

from setuptools import setup

setup(
    name='tomltable',
    version='1.1',
    description=u'command-line tool to generate TOML-defined regression tables from JSON data files',
    author=u'Gabor Nyeki',
    url='https://www.gabornyeki.com/',
    packages=['tomltable'],
    install_requires=['click', 'regex', 'toml'],
    provides=['tomltable (1.1)'],
    entry_points={
        'console_scripts': [
            'tomltable = tomltable:main',
        ],
    }
    )
