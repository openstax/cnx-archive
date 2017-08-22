# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest
import HTMLParser

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
        xpath_str = "//*[local-name()='definition']"

        self.request.params = {'id': uuid, 'q': xpath_str}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        expected = """<html xmlns="http://www.w3.org/1999/xhtml">\n  <body><ul><li><a href="/xpath.html?id=e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1&amp;q=//*[local-name()='definition']">College Physics</a>\
<ul><li><a href="/xpath.html?id=209deb1f-1a46-4369-9e0d-18674cf58a3e@7&amp;q=//*[local-name()='definition']">Preface</a>\
</li><li><a>Introduction: The Nature of Science and Physics</a>\
<ul><li><a href="/xpath.html?id=f3c9ab70-a916-4d8c-9256-42953287b4e9@3&amp;q=//*[local-name()='definition']">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a>\
</li><li><a href="/xpath.html?id=d395b566-5fe3-4428-bcb2-19016e3aa3ce@4&amp;q=//*[local-name()='definition']">Physics: An Introduction</a>\
</li><li><a href="/xpath.html?id=c8bdbabc-62b1-4a5f-b291-982ab25756d7@6&amp;q=//*[local-name()='definition']">Physical Quantities and Units</a>\
</li><li><a href="/xpath.html?id=5152cea8-829a-4aaf-bcc5-c58a416ecb66@7&amp;q=//*[local-name()='definition']">Accuracy, Precision, and Significant Figures</a>\
</li><li><a href="/xpath.html?id=5838b105-41cd-4c3d-a957-3ac004a48af3@5&amp;q=//*[local-name()='definition']">Approximation</a>\
</li></ul></li><li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a>\
<ul><li><a href="/xpath.html?id=24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2&amp;q=//*[local-name()='definition']">Introduction: Further Applications of Newton&#8217;s Laws</a>\
</li><li><a href="/xpath.html?id=ea271306-f7f2-46ac-b2ec-1d80ff186a59@5&amp;q=//*[local-name()='definition']">Friction</a>\
</li><li><a href="/xpath.html?id=26346a42-84b9-48ad-9f6a-62303c16ad41@6&amp;q=//*[local-name()='definition']">Drag Forces</a>\
</li><li><a href="/xpath.html?id=56f1c5c1-4014-450d-a477-2121e276beca@8&amp;q=//*[local-name()='definition']">Elasticity: Stress and Strain</a>\
</li></ul></li><li><a href="/xpath.html?id=f6024d8a-1868-44c7-ab65-45419ef54881@3&amp;q=//*[local-name()='definition']">Atomic Masses</a>\
</li><li><a href="/xpath.html?id=7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2&amp;q=//*[local-name()='definition']">Selected Radioactive Isotopes</a>\
</li><li><a href="/xpath.html?id=c0a76659-c311-405f-9a99-15c71af39325@5&amp;q=//*[local-name()='definition']">Useful Inf&#248;rmation</a>\
</li><li><a href="/xpath.html?id=ae3e18de-638d-4738-b804-dc69cd4db3a3@5&amp;q=//*[local-name()='definition']">Glossary of Key Symbols and Notation</a>\
</li></ul></li></ul></body>\n</html>\n"""
        # Call the view
        from ...views.xpath import xpath
        resp = xpath(self.request)

        # Check that the view returns the expected html
        self.assertMultiLineEqual(resp.body, expected)

    def test_xpath_page(self):
        # Test that the returned results from the xpath are correct.
        uuid = '5838b105-41cd-4c3d-a957-3ac004a48af3'
        xpath_str = "//*[local-name()='definition']"

        expected = {
            u'results': [
                {
                    u'xpath_results': [
                        u'<definition xmlns=\"http://cnx.rice.edu/cnxml\" id=\"import-auto-id2912380\">\n  <term>approximation</term>\n  <meaning id=\"fs-id1363258\"> an estimated value based on prior experience and reasoning</meaning>\n</definition>'
                    ],
                    u'name': u'Approximation',
                    u'uuid': u'5838b105-41cd-4c3d-a957-3ac004a48af3'
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
        self.request.params = {'id': '', 'q': "//*[local-name()='definition']"}
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
