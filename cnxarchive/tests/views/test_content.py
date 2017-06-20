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
from .views_test_data import COLLECTION_METADATA
from .views_test_data import COLLECTION_JSON_TREE
from .views_test_data import MODULE_METADATA
from .views_test_data import COLLECTION_DERIVED_METADATA

def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


@mock.patch('cnxarchive.views.content.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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

        from ...views.content import get_content

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

        from ...views.content import get_content

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

        from ...views.content import get_content

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

        from ...views.content import get_content

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
        from ...views.content import get_content

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
        from ...views.content import get_content

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
        from ...views.content import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_not_found(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': '98c44aed-056b-450a-81b0-61af87ee75af'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views.content import get_content
        self.assertRaises(IdentHashMissingVersion, get_content,
                          self.request)

    def test_content_not_found_w_invalid_uuid(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': 'notfound@1'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
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
        from ...views.content import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_collection_as_html(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        expected = u"""<html xmlns="http://www.w3.org/1999/xhtml">
  <body>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1.html">College Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:209deb1f-1a46-4369-9e0d-18674cf58a3e@7.html">Preface</a></li>\
<li><a>Introduction: The Nature of Science and Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:f3c9ab70-a916-4d8c-9256-42953287b4e9@3.html">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:d395b566-5fe3-4428-bcb2-19016e3aa3ce@4.html">Physics: An Introduction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:c8bdbabc-62b1-4a5f-b291-982ab25756d7@6.html">Physical Quantities and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:5152cea8-829a-4aaf-bcc5-c58a416ecb66@7.html">Accuracy, Precision, and Significant Figures</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:5838b105-41cd-4c3d-a957-3ac004a48af3@5.html">Approximation</a></li></ul></li>\
<li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2.html">Introduction: Further Applications of Newton’s Laws</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:ea271306-f7f2-46ac-b2ec-1d80ff186a59@5.html">Friction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:26346a42-84b9-48ad-9f6a-62303c16ad41@6.html">Drag Forces</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:56f1c5c1-4014-450d-a477-2121e276beca@8.html">Elasticity: Stress and Strain</a></li>\
</ul></li><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:f6024d8a-1868-44c7-ab65-45419ef54881@3.html">Atomic Masses</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2.html">Selected Radioactive Isotopes</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:c0a76659-c311-405f-9a99-15c71af39325@5.html">Useful Inførmation</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:ae3e18de-638d-4738-b804-dc69cd4db3a3@5.html">Glossary of Key Symbols and Notation</a></li></ul></li></ul></body>\n</html>\n"""

        # Build the environment
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(uuid, version),
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-html'

        # Call the view
        from ...views.content import get_content_html
        resp = get_content_html(self.request)

        # Check that the view returns the expected html
        p = HTMLParser.HTMLParser()
        self.assertMultiLineEqual(p.unescape(resp.body), expected)

    def test_content_module_as_html(self):
        uuid = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce'
        version = '4'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-html'

        # Call the view.
        from ...views.content import get_content_html

        # Check that the view returns some html
        resp_body = get_content_html(self.request).body
        self.assertTrue(resp_body.startswith('<html'))

    @testing.db_connect
    def test_content_index_html(self, cursor):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        cursor.execute('DELETE FROM module_files')
        # Insert a file for version 4
        cursor.execute('''INSERT INTO files (file, media_type) VALUES
            (%s, 'text/html') RETURNING fileid''', [memoryview('Version 4')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename) VALUES
                       (%s, %s, 'index.cnxml.html')''',
                       [16, fileid])
        # Insert a file for version 5
        cursor.execute('''INSERT INTO files (file, media_type) VALUES
            (%s, 'text/html') RETURNING fileid''', [memoryview('Version 5')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename) VALUES
                       (%s, %s, 'index.cnxml.html')''',
                       [15, fileid])
        cursor.connection.commit()

        def get_content(version):
            # Build the request environment
            self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
            self.request.matched_route = mock.Mock()
            self.request.matched_route.name = 'content'

            # Call the view
            from ...views.content import get_content
            content = get_content(self.request).json_body

            return content.pop('content')

        self.assertEqual(get_content(4), 'Version 4')
        self.assertEqual(get_content(5), 'Version 5')
