# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest
try:
    from unittest import mock  # python 3
except ImportError:
    import mock  # python 2
try:
    from urllib.parse import urljoin
except:
    from urlparse import urljoin

from .testing import integration_test_settings


class FunctionalTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = settings = integration_test_settings()
        # only run once for all the tests

        from .. import main
        app = main({}, **settings)

        from webtest import TestApp
        cls.testapp = TestApp(app)


class IdentHashSyntaxErrorTestCase(FunctionalTestCase):
    def test_get_export_invalid_id(self):
        self.testapp.get('/exports/abcd.pdf', status=404)

    def test_get_extra_invalid_id(self):
        self.testapp.get('/extras/abcd', status=404)

    def test_in_book_search_invalid_id(self):
        self.testapp.get('/search/abcd?q=air+or+liquid+drag',
                         status=404)

    def test_in_book_search_highlighted_results_invalid_id(self):
        self.testapp.get('/search/abcd:efgh?q=air+or+liquid+drag',
                         status=404)
