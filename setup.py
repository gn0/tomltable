#!/usr/bin/env python
# coding: utf8

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as handle:
    readme = handle.read()

setup(
    name="tomltable",
    version="1.1.1",
    description="command-line tool to generate TOML-defined regression tables from JSON data files",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Gabor Nyeki",
    url="https://codeberg.org/gnyeki/tomltable",
    packages=["tomltable"],
    install_requires=["click", "regex", "toml"],
    entry_points={
        "console_scripts": [
            "tomltable = tomltable:main",
        ],
    }
)
