# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import HTMLParser
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing
from pyramid import httpexceptions

from .. import testing
from ... import config
from .views_test_data import COLLECTION_METADATA


class XpathViewTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

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

        # Clear all cached searches
        import memcache
        mc_servers = self.settings['memcache-servers'].split()
        mc = memcache.Client(mc_servers, debug=0)
        mc.flush_all()
        mc.disconnect_all()

        # Patch database search so that it's possible to assert call counts
        # later
        from ... import cache
        original_search = cache.database_search
        self.db_search_call_count = 0

        def patched_search(*args, **kwargs):
            self.db_search_call_count += 1
            return original_search(*args, **kwargs)
        cache.database_search = patched_search
        self.addCleanup(setattr, cache, 'database_search', original_search)

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    def test_xpath_tree(self):
        # Test that the returned HTML tree is correct.
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        xpath_str = "//cnx:definition"

        self.request.params = {'id': uuid, 'q': xpath_str}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # Call the view
        from ...views.xpath import xpath
        resp = xpath(self.request)

        with open(os.path.join(testing.here, 'data/xpath.html')) as f:
            expected = f.read()

        # Check that the view returns the expected html
        self.assertMultiLineEqual(resp.body, expected)

    def test_xpath_page(self):
        # Test that the returned results from the xpath are correct.
        uuid = '5838b105-41cd-4c3d-a957-3ac004a48af3'
        xpath_str = "//cnx:definition"

        expected = {
            u'results': [
                {
                    u'xpath_results': [
                        u'<definition xmlns=\"http://cnx.rice.edu/cnxml\" id=\"import-auto-id2912380\">\n  <term>approximation</term>\n  <meaning id=\"fs-id1363258\"> an estimated value based on prior experience and reasoning</meaning>\n</definition>'
                    ],
                    u'name': u'Approximation',
                    u'uuid': u'5838b105-41cd-4c3d-a957-3ac004a48af3',
                    u'version': u'5',
                }
            ]
        }
        self.request.params = {'id': uuid, 'q': xpath_str}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'
        self.request.headers['ACCEPT'] = 'application/json'

        from ...views.xpath import xpath
        resp = xpath(self.request)

        self.assertEqual(resp.json_body, expected)

    def test_xpath_bad_request(self):
        # Test empty id and xpath
        self.request.params = {'id': '', 'q': ''}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        from ...views.xpath import xpath
        self.assertRaises(httpexceptions.HTTPBadRequest, xpath, self.request)

        # Test empty id
        self.request.params = {'id': '', 'q': "//cnx:definition"}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        from ...views.xpath import xpath
        self.assertRaises(httpexceptions.HTTPBadRequest, xpath, self.request)

        # Test empty xpath
        self.request.params = {'id': '5838b105-41cd-4c3d-a957-3ac004a48af3', 'q': ''}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        from ...views.xpath import xpath
        self.assertRaises(httpexceptions.HTTPBadRequest, xpath, self.request)
