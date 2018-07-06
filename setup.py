"""A setuptools based setup module for WG-Gesucht-Crawler-CLI"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from codecs import open
from os import path
from setuptools import setup, find_packages

import versioneer

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open(path.join(here, 'HISTORY.rst'), encoding='utf-8') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'beautifulsoup4==4.6.0',
    'certifi==2018.4.16',
    'chardet==3.0.4',
    'click==6.7',
    'idna==2.7',
    'requests==2.19.1',
    'urllib3==1.23',
]

test_requirements = []

setup(
    name='wg-gesucht-crawler-cli',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Python web crawler / scraper for WG-Gesucht. Crawls the WG-Gesucht site for new apartment listings and send a message to the poster, based off your saved filters and saved text template.",
    long_description=readme + '\n\n' + history,
    author="Grant Williams",
    author_email='grant.williams2986@gmail.com',
    url='https://github.com/grantwilliams/wg-gesucht-crawler-cli',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    entry_points={
        'console_scripts': [
            'wg-gesucht-crawler-cli=wg_gesucht.cli:cli',
        ],
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
