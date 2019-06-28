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
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'title': 'Preface to College Physics',
             'type': 'Module',
             'module_ident': 2,
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7',
             },
        ]
        self.assertEqual(results, expected)

    def test_for_book(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1'

        # TARGET
        results = self.target(ident_hash)

        expected = [
            {'ident_hash': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
             'title': 'College Physics',
             'type': 'Collection',
             'module_ident': 17,
             'uuid': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
             'version': '6.1',
             },
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'title': 'Preface',
             'type': 'Module',
             'module_ident': 2,
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7',
             },
        ]
        self.assertEqual(results, expected)

    def test_for_baked_book(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1'

        # TARGET
        results = self.target(ident_hash, True)

        expected = [
            {'ident_hash': '174c4069-2743-42e9-adfe-4c7084f81fc5@1',
             'module_ident': 20,
             'title': 'Collated page',
             'type': 'CompositeModule',
             'uuid': '174c4069-2743-42e9-adfe-4c7084f81fc5',
             'version': '1'},
            {'ident_hash': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
             'module_ident': 17,
             'title': 'College Physics',
             'type': 'Collection',
             'uuid': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
             'version': '6.1'},
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'module_ident': 2,
             'title': 'Preface',
             'type': 'Module',
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7'},
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
        self.assertRaises(TypeError, self.target, (1, 2, 3,), '//foo-elm', 'bar-type')

    def test_missing_book_context(self):
        self.assertRaises(ValueError, self.target, (1, 2, 3,), '//foo-elm', 'baked-html')

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

    def test_baked_html_page(self):
        docs = (20,)
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath = '//body'
        context = 17  # i.e. College Physics

        # TARGET
        results = self.target(docs, xpath, 'baked-html', context)

        expected = [
            (20, ['<body>test collated content</body>']),
        ]
        self.assertEqual(dict(results), dict(expected))


class XPathViewTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()
        cls.fixture.setUp()

    @classmethod
    def tearDownClass(cls):
        pyramid_testing.tearDown()
        cls.fixture.tearDown()

    def setUp(self):
        self.request = pyramid_testing.DummyRequest()
        self.request.headers['HOST'] = 'cnx.org'
        self.request.application_url = 'http://cnx.org'
        config = pyramid_testing.setUp(settings=self.settings,
                                       request=self.request)
        # Set up routes
        from ... import declare_api_routes
        declare_api_routes(config)

    def tearDown(self):
        pyramid_testing.tearDown()

    @property
    def target(self):
        from ...views.xpath import XPathView
        return XPathView

    def test_matching(self):
        # Test that the returned results from the xpath are correct.
        uuid = '5838b105-41cd-4c3d-a957-3ac004a48af3'
        xpath_str = "//cnx:definition"

        self.request.params = {'id': uuid, 'q': xpath_str}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '5838b105-41cd-4c3d-a957-3ac004a48af3@5',
             'matches': [
                 ('<definition xmlns="http://cnx.rice.edu/cnxml" id="import-auto-id2912380">\n  '
                  '<term>approximation</term>\n  <meaning id="fs-id1363258"> '
                  'an estimated value based on prior experience and reasoning</meaning>\n</definition>'
                  )],
             'title': 'Approximation',
             'type': 'Module',
             'uri': '/contents/5838b105-41cd-4c3d-a957-3ac004a48af3@5',
             'uuid': '5838b105-41cd-4c3d-a957-3ac004a48af3',
             'version': '5',
             },
        ]
        self.assertEqual(matches, expected)

    def test_matching_html(self):
        # Test that the returned results from the xpath are correct.
        uuid = '5838b105-41cd-4c3d-a957-3ac004a48af3'
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath_str = "//h:dl"

        self.request.params = {'id': uuid, 'q': xpath_str, 'type': 'html'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '5838b105-41cd-4c3d-a957-3ac004a48af3@5',
             'matches': [
                 ('<dl xmlns="http://www.w3.org/1999/xhtml" '
                  'id="import-auto-id2912380">\n  <dt>approximation</dt>\n  '
                  '<dd id="fs-id1363258"> an estimated value based on prior '
                  'experience and reasoning</dd>\n</dl>'
                  )],
             'title': 'Approximation',
             'type': 'Module',
             'uri': '/contents/5838b105-41cd-4c3d-a957-3ac004a48af3@5',
             'uuid': '5838b105-41cd-4c3d-a957-3ac004a48af3',
             'version': '5',
             },
        ]
        self.assertEqual(matches, expected)

    def test_matching_html_page(self):
        uuid = 'IJ3rHxpG'
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath_str = "//h:a"

        self.request.params = {'id': uuid, 'q': xpath_str, 'type': 'html'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'matches': [
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://openstaxcollege.org">'
                  'http://openstaxcollege.org</a>'),
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://openstaxcollege.org/textbooks/college-physics">'
                  'Student Solutions Manual and an Instructor Solutions Manual</a>'),
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://phet.colorado.edu">'
                  'http://phet.colorado.edu</a>'),
             ],
             'title': 'Preface to College Physics',
             'type': 'Module',
             'uri': '/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7',
             },
        ]
        self.assertEqual(matches, expected)

    def test_matching_html_page_in_book_context(self):
        uuid = '55_943-0@6.1:IJ3rHxpG'
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath_str = "//h:a"

        self.request.params = {'id': uuid, 'q': xpath_str, 'type': 'html'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'matches': [
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://openstaxcollege.org">'
                  'http://openstaxcollege.org</a>'),
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://openstaxcollege.org/textbooks/college-physics">'
                  'Student Solutions Manual and an Instructor Solutions Manual</a>'),
                 ('<a xmlns="http://www.w3.org/1999/xhtml" href="http://phet.colorado.edu">'
                  'http://phet.colorado.edu</a>'),
             ],
             'title': 'Preface to College Physics',
             'type': 'Module',
             'uri': '/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7',
             },
        ]
        self.assertEqual(matches, expected)

    def test_matching_baked_html_book(self):
        id = '55_943-0@6.1'  # a Collection
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath_str = "//body"

        self.request.params = {'id': id, 'q': xpath_str, 'type': 'baked-html'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'matches': ['<body>Page content after collation</body>'],
             'title': 'Preface',
             'type': 'Module',
             'uri': '/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'uuid': '209deb1f-1a46-4369-9e0d-18674cf58a3e',
             'version': '7'},
            {'ident_hash': '174c4069-2743-42e9-adfe-4c7084f81fc5@1',
             'matches': ['<body>test collated content</body>'],
             'title': 'Collated page',
             'type': 'CompositeModule',
             'uri': '/contents/174c4069-2743-42e9-adfe-4c7084f81fc5@1',
             'uuid': '174c4069-2743-42e9-adfe-4c7084f81fc5',
             'version': '1'},
        ]
        self.assertEqual(matches, expected)

    def test_matching_baked_html_page(self):
        id = '55_943-0@6.1:F0xAaSdD'
        # BUG in the data where the XML does not have a default namespace.
        # It should be `//h:body`.
        # However, this works and effectively exercises the problem
        # space, so roll with it.
        xpath_str = "//body"

        self.request.params = {'id': id, 'q': xpath_str, 'type': 'baked-html'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath'

        # TARGET
        matches = self.target(self.request).match_data

        expected = [
            {'ident_hash': '174c4069-2743-42e9-adfe-4c7084f81fc5@1',
             'matches': ['<body>test collated content</body>'],
             'title': 'Collated page',
             'type': 'CompositeModule',
             'uri': '/contents/174c4069-2743-42e9-adfe-4c7084f81fc5@1',
             'uuid': '174c4069-2743-42e9-adfe-4c7084f81fc5',
             'version': '1'},
        ]
        self.assertEqual(matches, expected)

    # HTTP exception tests
    ########################

    def test_missing_required_params(self):
        # Test empty id and xpath
        self.request.params = {'id': '', 'q': ''}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        # TARGET
        self.assertRaises(httpexceptions.HTTPBadRequest, self.target, self.request)

    def test_missing_id_param(self):
        # Test empty id
        self.request.params = {'id': '', 'q': "//cnx:definition"}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        # TARGET
        self.assertRaises(httpexceptions.HTTPBadRequest, self.target, self.request)

    def test_missing_query_param(self):
        # Test empty xpath
        self.request.params = {'id': '5838b105-41cd-4c3d-a957-3ac004a48af3', 'q': ''}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        # TARGET
        self.assertRaises(httpexceptions.HTTPBadRequest, self.target, self.request)

    def test_invalid_type_param(self):
        # Test empty xpath
        self.request.params = {
            'id': '5838b105-41cd-4c3d-a957-3ac004a48af3',
            'q': '//foo',
            'type': 'bar',
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'xpath-json'

        # TARGET
        self.assertRaises(httpexceptions.HTTPBadRequest, self.target, self.request)

    # def test_matching_baked_html_page_without_book_context(self):
    #     id = 'F0xAaSdD'  # a CompositeModule, but any Module would do
    #     # BUG in the data where the XML does not have a default namespace.
    #     # It should be `//h:body`.
    #     # However, this works and effectively exercises the problem
    #     # space, so roll with it.
    #     xpath_str = "//body"

    #     self.request.params = {'id': id, 'q': xpath_str, 'type': 'baked-html'}
    #     self.request.matched_route = mock.Mock()
    #     self.request.matched_route.name = 'xpath'

    #     # TARGET
    #     matches = self.target(self.request).match_data

    #     expected = [
    #     ]
    #     self.assertEqual(matches, expected)


class XPathSearchTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(XPathSearchTestCase, cls).setUpClass()
        cls.fixture.setUp()

    @classmethod
    def tearDownClass(cls):
        pyramid_testing.tearDown()
        cls.fixture.tearDown()

    def test_json(self):
        params = {
            'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
            'q': '//c:emphasis',
        }
        resp = self.testapp.get('/xpath.json', params)

        self.assertEqual(resp.status, '200 OK')
        expected = [
            {u'ident_hash': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             u'matches': [
                 u'<emphasis xmlns="http://cnx.rice.edu/cnxml" effect="italics">College Physics</emphasis>',
                 u'<emphasis xmlns="http://cnx.rice.edu/cnxml" effect="italics">College Physics</emphasis>',
             ],
             u'title': u'Preface',
             u'type': u'Module',
             u'uri': u'/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             u'uuid': u'209deb1f-1a46-4369-9e0d-18674cf58a3e',
             u'version': u'7',
             },
        ]
        self.assertEqual(resp.json, expected)

    def test_json_wo_matches(self):
        params = {
            'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
            'q': '//c:figure',
        }
        resp = self.testapp.get('/xpath.json', params)

        self.assertEqual(resp.status, '200 OK')
        expected = []
        self.assertEqual(resp.json, expected)

    def test_html(self):
        params = {
            'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
            'q': '//c:emphasis',
        }
        resp = self.testapp.get('/xpath.html', params)

        self.assertEqual(resp.status, '200 OK')
        with open(os.path.join(testing.here, 'data/xpath.html')) as f:
            expected = f.read().strip()
        self.assertEqual(resp.body, expected)

    def test_html_wo_matches(self):
        params = {
            'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
            'q': '//c:figure',
        }
        resp = self.testapp.get('/xpath.html', params)

        self.assertEqual(resp.status, '200 OK')
        self.assertIn('<span>No matches</span>', resp.body)
