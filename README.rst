===============================
WG Gesucht Crawler
===============================

.. image:: https://img.shields.io/travis/grantwilliams/wg-gesucht-crawler-cli.svg
        :target: https://travis-ci.org/grantwilliams/wg-gesucht-crawler-cli

.. image:: https://img.shields.io/pypi/v/wg-gesucht-crawler-cli.svg
        :target: https://pypi.python.org/pypi/wg-gesucht-crawler-cli

.. image:: https://readthedocs.org/projects/wg-gesucht-crawler-cli/badge/?version=latest
        :target: https://wg-gesucht-crawler-cli.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

Python web crawler / scraper for WG-Gesucht. Crawls the WG-Gesucht site for new apartment listings and send a message to the poster, based off your saved filters and saved text template.

Installation
------------
::

    $ pip install wg-gesucht-crawler-cli

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv wg-gesucht-crawler-cli
    $ pip install wg-gesucht-crawler-cli

Use
---
Can be run directly from the command line with::

    $ wg-gesucht-crawler-cli --help

Or if you want to use it in your own project:

.. code-block:: python

    from wg_gesucht.crawler import WgGesuchtCrawler

Just make sure to save at least one search filter as well as a template text on your wg-gesucht account.

* Free software: MIT license
* Documentation: https://wg-gesucht-crawler-cli.readthedocs.org.

Features
--------

* Searches https://wg-gesucht.de for new WG ads based off your saved filters
* Sends your saved template message and applies to all matching listings
* Reruns every ~5 minutes
* Run on a RPi or free EC2 micro instance 24/7 to always be one of the first to apply for new listings



**Getting Caught with reCAPTCHA**

I've made the crawler sleep for 5-8 seconds between each request to try and avoid their reCAPTCHA, but if the crawler does get caught, you can sign into your wg-gesucht account manually through the browser and solve the reCAPTCHA, then start the crawler again.
If it continues to happen, you can also increase the sleep time in the :code:`get_page()` function in :code:`wg_gesucht.py`
