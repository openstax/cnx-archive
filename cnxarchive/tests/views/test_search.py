# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import time
import json
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing
from pyramid.encode import url_quote
from pyramid.traversal import PATH_SAFE

from .. import testing


def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


SEARCH_RESULTS_FILEPATH = os.path.join(testing.DATA_DIRECTORY,
                                       'search_results.json')
with open(SEARCH_RESULTS_FILEPATH, 'r') as file:
    SEARCH_RESULTS = json.load(file)


class SearchViewsTestCase(unittest.TestCase):
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

    def test_search(self):
        # Build the request
        self.request.params = {'q': '"college physics" sort:version'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(sorted(results.keys()), sorted(SEARCH_RESULTS.keys()))
        self.maxDiff = None
        for key in results:
            self.assertEqual(results[key], SEARCH_RESULTS[key])

    def test_search_filter_by_authorID(self):
        # Build the request
        self.request.params = {'q': '"college physics" authorID:cnxcap'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['query'], {
            u'sort': [],
            u'per_page': 20,
            u'page': 1,
            u'limits': [{u'tag': u'text', u'value': u'college physics'},
                        {u'tag': u'authorID', u'index': 0,
                         u'value': u'cnxcap'}],
            })

    def test_author_special_case_search(self):
        '''
        Test the search case where an additional database query is needed to
        return auxiliary author info when the first query returned no
        results.
        '''

        # Build the request
        import string
        sub = u'subject:"Arguing with Judge Judy: Popular ‘Logic’ on TV Judge Shows"'
        auth0 = 'authorID:cnxcap'
        auth1 = 'authorID:OpenStaxCollege'
        auth2 = 'authorID:DrBunsenHoneydew'
        fields = [sub, auth0, auth1, auth2]
        self.request.params = {'q': string.join(fields, u' ')}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 0)

        expected = [
            {u'surname': u'Physics',
             u'firstname': u'College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OSC Physics Maintainer',
             u'id': u'cnxcap',
             },
            {u'surname': None,
             u'firstname': u'OpenStax College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OpenStax College',
             u'id': u'OpenStaxCollege',
             },
            {u'fullname': None,
             u'id': u'DrBunsenHoneydew',
             },
            ]

        auxiliary_authors = results['results']['auxiliary']['authors']

        self.assertEqual(auxiliary_authors, expected)

        # check to see if auxilary authors list is referenced
        # by the correct indexs in results['query']['limits']
        # list
        for limit in results['query']['limits']:
            if limit['tag'] == 'authorID':
                self.assertIn('index', limit.keys())
                idx = limit['index']
                aux_info = expected[idx]
                self.assertEqual(limit['value'], aux_info['id'])

    def test_search_only_subject(self):
        # From the Content page, we have a list of subjects (tags),
        # they link to the search page like: /search?q=subject:"Arts"

        # Build the request
        self.request.params = {'q': 'subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [{u'tag': u'subject', u'value': u'Science and Technology'}],
            u'sort': []})
        self.assertEqual(results['results']['total'], 7)

    def test_search_w_html_title(self):
        # Build the request
        self.request.params = {'q': 'title:"Derived Copy of College Physics" type:book'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [
                {u'tag': u'title', u'value': u'Derived Copy of College Physics'},
                {u'tag': u'type', u'value': u'book'},
                ],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_w_title_sort_pubDate(self):
        # Build the request
        self.request.params = {'q': 'title:"Derived Copy of College Physics" type:book sort:pubDate'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [
                {u'tag': u'title', u'value': u'Derived Copy of College Physics'},
                {u'tag': u'type', u'value': u'book'},
                ],
            u'sort': ['pubDate']})
        self.assertEqual(results['results']['total'], 1)

    def test_search_with_subject(self):
        # Build the request
        self.request.params = {'q': 'title:"college physics" subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [
                {u'tag': u'title', u'value': u'college physics'},
                {u'tag': u'subject', u'value': 'Science and Technology'},
                ],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_highlight_abstract(self):
        # Build the request
        self.request.params = {'q': '"college physics"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(
            results['results']['items'][0]['summarySnippet'],
            'algebra-based, two-semester <b>college</b> <b>physics</b> book '
            'is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental '
            '<b>physics</b> concepts. This online, fully editable and '
            'customizable title includes learning objectives, concept '
            'questions, links to labs and simulations, and ample practice '
            'opportunities to solve traditional <b>physics</b> application '
            'problems. ')

        self.assertEqual(
            results['results']['items'][1]['summarySnippet'],
            'algebra-based, two-semester <b>college</b> <b>physics</b> book '
            'is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental '
            '<b>physics</b> concepts. This online, fully editable and '
            'customizable title includes learning objectives, concept '
            'questions, links to labs and simulations, and ample practice '
            'opportunities to solve traditional <b>physics</b> application '
            'problems. ')
        self.assertEqual(results['results']['items'][2]['summarySnippet'],
                         ' A number list:   one  two  three   ')

        # Test for no highlighting on specific field queries.
        self.request.params = {'q': 'title:"college physics"'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(
            results['results']['items'][0]['summarySnippet'],
            ' This introductory, algebra-based, two-semester college physics '
            'book is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental physics '
            'concepts. This online, fully editable and customizable title '
            'includes learning objectives, concept questions, links to labs '
            'and simulations, and ample practice opportunities to solve '
            'traditional')
        self.assertEqual(
            results['results']['items'][1]['summarySnippet'],
            ' This introductory, algebra-based, two-semester college physics '
            'book is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental physics '
            'concepts. This online, fully editable and customizable title '
            'includes learning objectives, concept questions, links to labs '
            'and simulations, and ample practice opportunities to solve '
            'traditional')

        self.assertEqual(results['results']['items'][2]['summarySnippet'],
                         ' A number list:   one  two  three   ')

    def test_search_no_params(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results, {
            u'query': {
                u'limits': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [],
                },
            })

    def test_search_whitespace(self):
        self.request.params = {'q': ' '}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results, json.dumps({
            u'query': {
                u'limits': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [],
                },
            }))

    def test_search_utf8(self):
        self.request.params = {'q': u'"你好"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': u'你好'}],
                u'sort': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_punctuations(self):
        self.request.params = {'q': r":\.+'?"}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': ur":\.+'?"}],
                u'sort': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_unbalanced_quotes(self):
        self.request.params = {'q': r'"a phrase" "something else sort:pubDate author:"first last"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [
                    {u'tag': u'text', u'value': u'a phrase'},
                    {u'tag': u'text', u'value': u'something else'},
                    {u'tag': u'author', u'value': 'first last'},
                    ],
                u'sort': [u'pubDate'],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_type_page_or_module(self):
        # Test searching "page"

        # Build the request
        self.request.params = {'q': 'title:"college physics" type:page'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'page'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.module')

        # Test searching "module"

        # Build the request
        self.request.params = {'q': '"college physics" type:module'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'module'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.module')

    def test_search_type_book_or_collection(self):
        # Test searching "book"

        # Build the request
        self.request.params = {'q': 'title:physics type:book'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'book'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.collection')

        # Test searching "collection"

        # Build the request
        self.request.params = {'q': 'title:physics type:collection'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'collection'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.collection')

    def test_search_wo_cache(self):
        # Patch settings so caching is disabled
        settings = dict(self.settings).copy()
        settings['memcache-servers'] = ''
        config_kwargs = dict(settings=settings, request=self.request)
        from ...views.search import search

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        def call_search_view():
            with pyramid_testing.testConfig(**config_kwargs):
                return search(self.request)

        results = call_search_view().json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 6)
        self.assertEqual(len(results['results']['items']), 3)

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        results = call_search_view().json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 6)
        self.assertEqual(len(results['results']['items']), 3)

        # Made 4 requests, so should have called db search 4 times
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_pagination(self):
        # Test search results with pagination

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'sort': [],
            'limits': [{'tag': 'text', 'value': 'introduction'}],
            'per_page': 3,
            'page': 1,
            })
        self.assertEqual(results['results']['total'], 6)
        self.assertEqual(len(results['results']['items']), 3)
        self.assertEqual(
                results['results']['items'][0]['title'],
                'College Physics')
        self.assertEqual(
                results['results']['items'][1]['title'],
                '<span style="color:red;">Derived</span>'
                ' Copy of College <i>Physics</i>')
        self.assertEqual(
                results['results']['items'][2]['title'],
                u'Introduction to Science and the Realm of Physics,'
                ' Physical Quantities, and Units')
        pub_year = [limit['values'] for limit in results['results']['limits']
                    if limit['tag'] == 'pubYear'][0]
        self.assertEqual(pub_year, [{'value': '2013', 'count': 6}])

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'sort': [],
            'limits': [{'tag': 'text', 'value': 'introduction'}],
            'per_page': 3,
            'page': 2,
            })
        self.assertEqual(results['results']['total'], 6)
        self.assertEqual(len(results['results']['items']), 3)
        self.assertEqual(results['results']['items'][0]['title'],
                         'Physics: An Introduction')
        self.assertEqual(results['results']['items'][1]['title'],
                         u'Introduction: Further Applications'
                         u' of Newton\u2019s Laws')
        pub_year = [limit['values'] for limit in results['results']['limits']
                    if limit['tag'] == 'pubYear'][0]
        self.assertEqual(pub_year, [{'value': '2013', 'count': 6}])

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '3'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        # Fetching all the pages should only query the
        # database once because the result should already
        # been cached in memcached
        self.assertEqual(self.db_search_call_count, 1)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_nocache(self):
        # Disable caching from url with nocache=True

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Search again but with caching disabled
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'nocache': 'True'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_cache_expired(self):
        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Fetch next page (should use cache)
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Wait for cache to expire
        time.sleep(60)

        # Fetch the same page (cache expired)
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_normal_cache(self):
        # Build the request
        self.request.params = {'q': '"college physics"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again after cache is expired
        time.sleep(20)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_long_cache(self):
        # Test searches which should be cached for longer

        # Build the request for subject search
        self.request.params = {'q': 'subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        time.sleep(20)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again after cache is expired
        time.sleep(15)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_memcached_key_length_error(self):
        # create a really long search query
        self.request.params = {
            'q': 'subject:"Science and Technology" pubYear:"2013" type:"Book"'
                 ' physics introduction examples college online learning and'
                 ' algebra'
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ...views.search import search
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 1)
