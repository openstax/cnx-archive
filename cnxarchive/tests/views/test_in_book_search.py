# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing

from ...utils import IdentHashShortId, IdentHashMissingVersion
from .. import testing


class InBookViewsTestCase(unittest.TestCase):
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

    def test_in_book_search_wo_version(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': id}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ...views.in_book_search import in_book_search
        with self.assertRaises(IdentHashMissingVersion) as cm:
            in_book_search(self.request)

    def test_in_book_search_shortid(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ...utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {'ident_hash':
                                  '{}@{}'.format(short_id, version)}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ...views.in_book_search import in_book_search
        with self.assertRaises(IdentHashShortId) as cm:
            in_book_search(self.request)

    def test_in_book_search_short_id_wo_version(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ...utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {'ident_hash': short_id}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ...views.in_book_search import in_book_search
        with self.assertRaises(IdentHashShortId) as cm:
            in_book_search(self.request)

    def test_in_book_search(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        # search query param
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        from ...views.in_book_search import in_book_search
        results = in_book_search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        IN_BOOK_SEARCH_RESULT = {
            u'results': {
                u'items': [{
                    u'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                    u'matches': u'3',
                    u'rank': u'0.05',
                    u'snippet': u'have in mind the forces of friction, '
                                u'<span class="q-match">air</span> or '
                                u'<span class="q-match">liquid</span> '
                                u'<span class="q-match">drag</span>, '
                                u'and deformation',
                    u'title': u'Introduction: Further Applications of '
                              u'Newton\u2019s Laws'}, {
                    u'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                    u'matches': u'77',
                    u'rank': u'0.00424134',
                    u'snippet': u'absence of <span '
                                u'class="q-match">air</span> <span '
                                u'class="q-match">drag</span> (b) with '
                                u'<span class="q-match">air</span> <span '
                                u'class="q-match">drag</span>. Take the '
                                u'size across of the drop',
                    u'title': u'<span class="q-match">Drag</span> Forces'}, {
                    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca@8',
                    u'matches': u'13',
                    u'rank': u'2.59875e-05',
                    u'snippet': u'compress gases and extremely difficult '
                                u'to compress <span '
                                u'class="q-match">liquids</span> and '
                                u'solids. For example, <span '
                                u'class="q-match">air</span> in a wine '
                                u'bottle is compressed when',
                    u'title': u'Elasticity: Stress and Strain'}],
                u'query': {u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
                           u'search_term': u'air or liquid drag'},
                u'total': 3}}

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results, IN_BOOK_SEARCH_RESULT)

    def test_in_book_search_highlighted_results_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_version = '8'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': book_uuid,
                                  'page_ident_hash': page_uuid}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search-page'

        # Call the view.
        from ...views.in_book_search import in_book_search_highlighted_results

        with self.assertRaises(IdentHashMissingVersion) as cm:
            in_book_search_highlighted_results(self.request)

    def test_in_book_search_highlighted_results(self):
        collection_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        collection_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_version = '8'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(collection_uuid, collection_version),
                                  'page_ident_hash': '{}@{}'.format(page_uuid, page_version)}
        # search query param
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search-page'

        from ...views.in_book_search import in_book_search_highlighted_results
        results = in_book_search_highlighted_results(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        title = results['results']['items'][0]['title']
        id = results['results']['items'][0]['id']
        content = results['results']['items'][0]['html']

        self.assertEqual(status, '200 OK')
        self.assertEqual(len(results['results']['items']), 1)
        self.assertEqual(content_type, 'application/json')
        self.assertEqual('Elasticity: Stress and Strain', title)
        self.assertEqual('56f1c5c1-4014-450d-a477-2121e276beca@8', id)
        self.assertEqual("<mtext class=\"q-match\">air</mtext>" in content,
                         True)

    def test_in_collated_book_search(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        # search query param
        self.request.params = {'q': 'collated'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        from ...views.in_book_search import in_book_search
        results = in_book_search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        IN_BOOK_SEARCH_RESULT = {
            'results': {
                'query': {
                    'search_term': 'collated',
                    'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1'
                    },
                'total': 2,
                'items': [
                    {
                        'snippet': 'Page content after <span class="q-match">collation</span>',
                        'matches': 'None',
                        'id': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                        'rank': '0.1',
                        'title': 'Preface'
                        },
                    {
                        'snippet': 'test <span class="q-match">collated</span> content',
                        'matches': 'None',
                        'id': '174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                        'rank': '0.1',
                        'title': '<span class="q-match">Collated</span> page'
                        }
                    ]
                }
            }

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results, IN_BOOK_SEARCH_RESULT)

    def test_in_collated_book_search_highlighted_results(self):
        collection_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        collection_version = '6.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(collection_uuid, collection_version),
                                  'page_ident_hash': '{}@{}'.format(page_uuid, page_version)}
        # search query param
        self.request.params = {'q': 'collated'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search-page'

        from ...views.in_book_search import in_book_search_highlighted_results
        results = in_book_search_highlighted_results(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        title = results['results']['items'][0]['title']
        id = results['results']['items'][0]['id']
        content = results['results']['items'][0]['html']

        self.assertEqual(status, '200 OK')
        self.assertEqual(len(results['results']['items']), 1)
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual('Preface', title)
        self.assertEqual('209deb1f-1a46-4369-9e0d-18674cf58a3e@7', id)
        self.assertEqual("<mtext class=\"q-match\">collation</mtext>" in content,
                         True)
