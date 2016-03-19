#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

LONG_DESCRIPTION = open('README.md').read()

setup(
    name="django-loadjson",
    version='0.1.0',
    description="Loadjson management command for Django",
    long_description=LONG_DESCRIPTION,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: Django",
        "Framework :: Django :: 1.7",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        "Intended Audience :: Developers"
    ],
    keywords='django management json',
    author="Terry Yanchynskyy",
    author_email='tarasics@gmail.com',
    url='https://github.com/onebit0fme/django-loadjson',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    test_suite='testrunner',
    install_requires=[
        'django>=1.7',
        'python-dateutil',
        'six',
    ],
    zip_safe=False,
)
