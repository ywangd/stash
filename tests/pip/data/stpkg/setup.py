# -*- coding: utf-8 -*-
"""setup.py for a local test package."""

from setuptools import setup


setup(
    name="stpkg",
    version="1.0.0",
    author="bennr01",
    description="local test package for StaSh pip. DO NOT UPLOAD!",
    keywords="test",
    url="https://github.com/ywangd/stash/",
    classifiers=[
        "Topic :: Test",
    ],
    py_modules=[
        "stpkg",
    ],
    entry_points={
        "console_scripts": [
            "stash_pip_test = stpkg:main"
        ],
    },
)
