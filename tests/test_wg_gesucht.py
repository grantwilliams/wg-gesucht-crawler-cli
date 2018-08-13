#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_wg_gesucht
----------------------------------

Tests for `wg_gesucht` module.
"""

import os
import sys
import unittest

import wg_gesucht
from wg_gesucht.crawler import WgGesuchtCrawler

home_path = 'HOMEPATH' if sys.platform == 'win32' else 'HOME'
dirname = os.path.join(os.environ[home_path], 'WG Finder')
wg_ad_links = os.path.join(dirname, "WG Ad Links")
offline_ad_links = os.path.join(dirname, "Offline Ad Links")
logs_folder = os.path.join(dirname, 'logs')
user_folder = os.path.join(dirname, '.user')
login_info_file = os.path.join(user_folder, '.login_info.json')

new_WgGesuchtCrawler = WgGesuchtCrawler(login_info_file, wg_ad_links,
                                        offline_ad_links, logs_folder)
class Testwg_gesucht(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        assert(wg_gesucht.__version__)

    def tearDown(self):
        pass

    def test_substitute_name_with_title(self):
        self.assertEqual(WgGesuchtCrawler.substitute_name(new_WgGesuchtCrawler,
                                                          'Vorname', 'Herr Hans Muster'),'Herr Hans Muster')

        self.assertEqual(WgGesuchtCrawler.substitute_name(new_WgGesuchtCrawler,
                                             'Vorname','Frau Hanna Muster'), 'Frau Hanna Muster')
    def test_substitute_name_withOut_title(self):
        self.assertEqual(WgGesuchtCrawler.substitute_name(new_WgGesuchtCrawler,
                                                          'Vorname', 'Hans Muster'), 'Hans')
        self.assertEqual(WgGesuchtCrawler.substitute_name(new_WgGesuchtCrawler,
                                                          'Vorname', 'Hanna'), 'Hanna')
