# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing

from .. import testing


class SitemapViewsTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = 10000

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        self.request = pyramid_testing.DummyRequest()
        self.request.headers['HOST'] = 'cnx.org'
        self.request.application_url = 'http://cnx.org'
        config = pyramid_testing.setUp(settings=self.settings,
                                       request=self.request)

        # Set up routes
        from ... import declare_api_routes
        declare_api_routes(config)

        # Set up type info
        from ... import declare_type_info
        declare_type_info(config)

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    def test_sitemap(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'sitemap'

        # Call the view
        from ...views.sitemap import sitemap
        sitemap = sitemap(self.request).body
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'sitemap.xml')
        with open(expected_file, 'r') as file:
            self.assertMultiLineEqual(sitemap, file.read())
