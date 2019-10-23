# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from datetime import datetime
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
        self.request.matchdict = {'from_id': 'OpenStaxCollege'}
        # Call the view
        from ...views.sitemap import sitemap
        this_sitemap = sitemap(self.request).body
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'sitemap.xml')
        with open(expected_file, 'r') as f:
            self.assertMultiLineEqual(this_sitemap, f.read())

    @mock.patch('cnxarchive.sitemap.datetime')
    def test_sitemap_index(self, mock_datetime):
        from ...views import sitemap

        utcnow = mock_datetime.datetime.utcnow
        utcnow.return_value = datetime(2017, 10, 29, 17, 44, 56, 875614)
        with mock.patch.object(sitemap, 'SITEMAP_LIMIT', 10):
            sitemap_index = sitemap.sitemap_index(self.request).body
            expected_file = os.path.join(testing.DATA_DIRECTORY,
                                         'sitemap_index.xml')
            with open(expected_file, 'r') as f:
                self.assertMultiLineEqual(sitemap_index, f.read())

            from lxml import etree
            import re
            ID_RE = re.compile('/sitemap-(.+).xml')

            si_tree = etree.XML(sitemap_index)
            for loc in si_tree.xpath('//s:loc/text()',
                                     namespaces={'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                fromid = ID_RE.search(loc).groups()[0]

                self.request.matchdict = {
                    'from_id': fromid,
                }

                sitemap_sub = sitemap.sitemap(self.request).body
                expected_file = os.path.join(testing.DATA_DIRECTORY,
                                             'sitemap-{}.xml'.format(fromid))
                with open(expected_file, 'r') as f:
                    self.assertMultiLineEqual(sitemap_sub, f.read())
