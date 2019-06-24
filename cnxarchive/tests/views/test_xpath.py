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


class LookupDocumentsToQueryTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()
        cls.fixture.setUp()

    def setUp(self):
        config = pyramid_testing.setUp(settings=self.settings)

    @classmethod
    def tearDownClass(cls):
        pyramid_testing.tearDown()
        cls.fixture.tearDown()

    @property
    def target(self):
        from cnxarchive.views.xpath import lookup_documents_to_query
        return lookup_documents_to_query

    def test_for_page(self):
        ident_hash = '209deb1f-1a46-4369-9e0d-18674cf58a3e@7'

        # TARGET
        results = self.target(ident_hash)

        expected = [
            {'major_version': 7,
             'name': 'Preface to College Physics',
             'portal_type': 'Module',
             'module_ident': 2,
             'minor_version': None,
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
            },
        ]
        self.assertEqual(results, expected)

    def test_for_book(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1'

        # TARGET
        results = self.target(ident_hash)

        expected = [
            {'major_version': 6,
             'name': 'College Physics',
             'portal_type': 'Collection',
             'module_ident': 17,
             'minor_version': 1,
             'uuid': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
            },
            {'major_version': 7,
             'name': 'Preface',
             'portal_type': 'Module',
             'module_ident': 2,
             'minor_version': None,
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
            },
        ]
        self.assertEqual(results, expected)

    def test_for_baked_book(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1'

        # TARGET
        results = self.target(ident_hash, True)

        expected = [
            {'major_version': 1,
             'minor_version': None,
             'module_ident': 20,
             'name': 'Collated page',
             'portal_type': 'CompositeModule',
             'uuid': '174c4069-2743-42e9-adfe-4c7084f81fc5'},
            {'major_version': 6,
             'minor_version': 1,
             'module_ident': 17,
             'name': 'College Physics',
             'portal_type': 'Collection',
             'uuid': 'e79ffde3-7fb4-4af3-9ec8-df648b391597'},
            {'major_version': 7,
             'minor_version': None,
             'module_ident': 2,
             'name': 'Preface',
             'portal_type': 'Module',
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e'},
        ]
        self.assertEqual(sorted(results), sorted(expected))


class QueryDocumentsByXPathTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()
        cls.fixture.setUp()

    def setUp(self):
        config = pyramid_testing.setUp(settings=self.settings)

    @classmethod
    def tearDownClass(cls):
        pyramid_testing.tearDown()
        cls.fixture.tearDown()

    @property
    def target(self):
        from cnxarchive.views.xpath import query_documents_by_xpath
        return query_documents_by_xpath

    # Error tests
    ###############

    def test_invalid_type(self):
        self.assertRaises(TypeError, self.target, (1,2,3,), '//foo-elm', 'bar-type')

    # Page tests
    ##############

    def test_page_without_matches(self):
        docs = (7,)
        xpath = '//c:link'

        # TARGET
        results = self.target(docs, xpath)

        expected = []
        self.assertEqual(results, expected)

    def test_cnxml_page(self):
        docs = (7,)
        xpath = '//c:emphasis'

        # TARGET
        results = self.target(docs, xpath)

        expected = [
            (7,
             ['<emphasis xmlns="http://cnx.rice.edu/cnxml">Strategy</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml">Solution</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml">Discussion</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml">Strategy</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml">Solution</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml">Discussion</emphasis>',
              ('<emphasis xmlns="http://cnx.rice.edu/cnxml" '
               'effect="italics">Salmonella typhimurium</emphasis>'),
              ]),
        ]
        self.assertEqual(results, expected)

    def test_html_page(self):
        docs = (7,)
        xpath = '//h:strong'

        # TARGET
        results = self.target(docs, xpath, 'html')

        expected = [
            (7,
             ['<strong xmlns="http://www.w3.org/1999/xhtml">Strategy</strong>',
              '<strong xmlns="http://www.w3.org/1999/xhtml">Solution</strong>',
              '<strong xmlns="http://www.w3.org/1999/xhtml">Discussion</strong>',
              '<strong xmlns="http://www.w3.org/1999/xhtml">Strategy</strong>',
              '<strong xmlns="http://www.w3.org/1999/xhtml">Solution</strong>',
              '<strong xmlns="http://www.w3.org/1999/xhtml">Discussion</strong>',
             ]),
        ]
        self.assertEqual(results, expected)

    def test_baked_html_page_without_context(self):
        docs = (2,)
        xpath = '//h:strong'

        # TARGET
        self.assertRaises(ValueError, self.target, docs, xpath, 'baked-html')

    def test_baked_html_page_with_context(self):
        docs = (2,)
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath = '//body'
        context = 17  # i.e. College Physics

        # TARGET
        results = self.target(docs, xpath, 'baked-html', context)

        expected = [(2, ['<body>Page content after collation</body>'])]
        self.assertEqual(results, expected)

    def test_baked_html_composite_page_with_context(self):
        docs = (20,)
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath = '//body'
        context = 17  # i.e. College Physics

        # TARGET
        results = self.target(docs, xpath, 'baked-html', context)

        expected = [(20, ['<body>test collated content</body>'])]
        self.assertEqual(results, expected)

    # Book tests
    ##############

    def test_book_without_matches(self):
        docs = (21,)
        xpath = '//c:link'

        # TARGET
        results = self.target(docs, xpath)

        expected = []
        self.assertEqual(results, expected)

    def test_cnxml_book(self):
        docs = (17, 2,)
        xpath = '//c:emphasis'

        # TARGET
        results = self.target(docs, xpath)

        expected = [
            (2,
             ['<emphasis xmlns="http://cnx.rice.edu/cnxml" effect="italics">College Physics</emphasis>',
              '<emphasis xmlns="http://cnx.rice.edu/cnxml" effect="italics">College Physics</emphasis>',
             ],
            ),
        ]
        self.assertEqual(results, expected)

    def test_html_book(self):
        docs = (17, 2,)
        xpath = '//h:em'

        # TARGET
        results = self.target(docs, xpath, 'html')

        expected = [
            (2,
             ['<em xmlns="http://www.w3.org/1999/xhtml" data-effect="italics">College Physics</em>',
              '<em xmlns="http://www.w3.org/1999/xhtml" data-effect="italics">College Physics</em>'],
            ),
        ]
        self.assertEqual(results, expected)

    def test_baked_html_book(self):
        docs = (17, 2, 20,)
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath = '//body'
        context = 17  # i.e. College Physics

        # TARGET
        results = self.target(docs, xpath, 'baked-html', context)

        expected = [
            (2, ['<body>Page content after collation</body>']),
            (20, ['<body>test collated content</body>']),
        ]
        self.assertEqual(dict(results), dict(expected))


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
