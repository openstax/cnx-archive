# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import datetime
import glob
import HTMLParser
import time
import json
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing
from pyramid.encode import url_quote
from pyramid.traversal import PATH_SAFE

from ...utils import IdentHashShortId, IdentHashMissingVersion
from .. import testing
from ..test_views import COLLECTION_METADATA
from ..test_views import COLLECTION_JSON_TREE
from ..test_views import MODULE_METADATA
from ..test_views import COLLECTION_DERIVED_METADATA

def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


@mock.patch('cnxarchive.views.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
class ViewsTestCase(unittest.TestCase):
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

    def test_collection_content(self):
        # Test for retrieving a piece of content.
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(COLLECTION_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], COLLECTION_METADATA[key])
        self.maxDiff = 10000
        # Check the tree for accuracy.
        self.assertEqual(content_tree, COLLECTION_JSON_TREE)

    def test_derived_collection(self):
        # Test for retrieving a piece of content.
        uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        version = '1.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()),
                         sorted(COLLECTION_METADATA.keys()))
        for key in COLLECTION_DERIVED_METADATA['parent']:
            self.assertEqual(content['parent'][key],
                             COLLECTION_DERIVED_METADATA['parent'][key])

    def test_content_collated_collection(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        # Check the tree.
        self.assertEqual({
            u'id': u'{}@{}'.format(uuid, version),
            u'shortId': u'55_943-0@6.1',
            u'title': u'College Physics',
            u'contents': [
                {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 u'shortId': u'IJ3rHxpG@7',
                 u'title': u'Preface'},
                {u'id': u'174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                 u'shortId': u'F0xAaSdD@1',
                 u'title': u'Collated page'},
                ],
            }, content['tree'])

    def test_content_uncollated_collection(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.GET = {'as_collated': False}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        # Check the tree.
        self.assertEqual({
            u'id': u'{}@{}'.format(uuid, version),
            u'shortId': u'55_943-0@6.1',
            u'title': u'College Physics',
            u'contents': [
                {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 u'shortId': u'IJ3rHxpG@7',
                 u'title': u'Preface'},
                ],
            }, content['tree'])

    @testing.db_connect
    def _create_empty_subcollections(self, cursor):
        cursor.execute("""\
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9100, 91, 'Empty Subcollections', 1, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9200, 9100, 'empty 1', 1, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9300, 9100, 'empty 2', 2, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9400, 91, 'Empty Subcollection', 4, true);
""")

    def test_empty_subcollection_content(self):
        self._create_empty_subcollections()

        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'
        from ...utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        content_tree = content.pop('tree')

        self.assertEqual(content_tree, {
            u'id': u'{}@{}'.format(uuid, version),
            u'shortId': u'{}@{}'.format(short_id, version),
            u'title': u'College Physics',
            u'contents': [
                {
                    u'id': u'subcol',
                    u'shortId': u'subcol',
                    u'title': u'Empty Subcollections',
                    u'contents': [
                        {
                            u'id': u'subcol',
                            u'shortId': u'subcol',
                            u'title': u'empty 1',
                            u'contents': [],
                            },
                        {
                            u'id': u'subcol',
                            u'shortId': u'subcol',
                            u'title': u'empty 2',
                            u'contents': [],
                            },

                        ],
                    },
                {
                    u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                    u'shortId': u'IJ3rHxpG@7',
                    u'title': u'Preface',
                    },
                {
                    u'id': u'174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                    u'shortId': u'F0xAaSdD@1',
                    u'title': u'Collated page',
                    },
                {
                    u'id': u'subcol',
                    u'shortId': u'subcol',
                    u'title': u'Empty Subcollection',
                    u'contents': [],
                    },
                ],
            })

    def test_history_metadata(self):
        # Test for the history field in the metadata
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        # History should only include displayed version and older versions
        self.assertEqual(content['history'], [{
            u'version': u'6.1',
            u'revised': u'2013-07-31T19:07:20Z',
            u'changes': u'Updated something',
            u'publisher': {
                u'surname': None,
                u'firstname': u'OpenStax College',
                u'suffix': None,
                u'title': None,
                u'id': u'OpenStaxCollege',
                u'fullname': u'OpenStax College',
                },
            }])

    def test_module_content(self):
        # Test for retreiving a module.
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ...views_folder.content import get_content

        content = get_content(self.request).json_body

        # Remove the 'content' text from the content for separate testing.
        content_text = content.pop('content')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(MODULE_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], MODULE_METADATA[key],
                             u'content[{key}] = {v1} but MODULE_METADATA[{key}] = {v2}'.format(
                             key=key, v1=content[key], v2=MODULE_METADATA[key]))

        # Check the content is the html file.
        self.assertTrue(content_text.find('<html') >= 0)

    def test_content_composite_page_wo_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ...views_folder.content import get_content

        # Composite modules cannot be retrieved outside of a collection
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_composite_page_in_wrong_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(uuid, version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ...views_folder.content import get_content

        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_composite_page_in_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(uuid, version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ...views_folder.content import get_content

        content = get_content(self.request).json_body

        # Check the media type.
        self.assertEqual(
            'application/vnd.org.cnx.composite-module',
            content['mediaType'])

        # Check the content.
        self.assertEqual(
            '<html><body>test collated content</body></html>',
            content['content'])

    def test_content_without_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': uuid,
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_content(self.request)

    def test_content_shortid_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        version = 5
        from ...utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': "{}@{}".format(short_id, version)
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_shortid_no_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        from ...utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': short_id
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_not_found(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': '98c44aed-056b-450a-81b0-61af87ee75af'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        self.assertRaises(IdentHashMissingVersion, get_content,
                          self.request)

    def test_content_not_found_w_invalid_uuid(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': 'notfound@1'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        self.assertRaises(IdentHashShortId, get_content,
                          self.request)

    def test_content_collated_page_inside_book(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        self.assertEqual(
            '<html><body>Page content after collation</body></html>\n',
            content['content'])

    def test_content_uncollated_page_inside_book(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
            'separator': ':',
            }
        self.request.GET = {'as_collated': False}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        from pyramid.httpexceptions import HTTPFound
        with self.assertRaises(HTTPFound) as caught_exc:
            get_content(self.request).json_body

        self.assertIn(
            'contents/{}'.format(page_uuid),
            dict(caught_exc.exception.headerlist)['Location'])

    def test_content_uncollated_composite_page_inside_book(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'
        page_uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        page_version = '1'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
            'separator': ':',
            }
        self.request.GET = {'as_collated': False}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        from pyramid.httpexceptions import HTTPNotFound
        with self.assertRaises(HTTPNotFound):
            get_content(self.request).json_body

    def test_content_uncollated_page(self):
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(page_uuid, page_version),
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ...views_folder.content import get_content
        content = get_content(self.request).json_body

        self.assertNotEqual(
            '<html><body>Page content after collation</body></html>\n',
            content['content'])

    def test_content_page_inside_book_version_mismatch(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_uuid, book_version),
                'page_ident_hash': '{}@0'.format(page_uuid),
                'separator': ':',
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_page_inside_book_w_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_uuid, book_version),
                'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
                'separator': ':',
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            get_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(
            cm.exception.headers['Location'],
            quote('/contents/{}@{}'.format(page_uuid, page_version)))

    def test_content_page_inside_book_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
            'ident_hash': book_uuid,
            'page_ident_hash': page_uuid,
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_content(self.request)

    def test_content_page_inside_book_version_mismatch_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ...utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_shortid, book_version),
                'page_ident_hash': '{}@0'.format(page_shortid),
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_page_inside_book_w_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ...utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_shortid, book_version),
                'page_ident_hash': '{}@{}'.format(page_shortid, page_version),
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_page_inside_book_wo_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ...utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
            'ident_hash': book_shortid,
            'page_ident_hash': page_shortid,
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views_folder.content import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)
