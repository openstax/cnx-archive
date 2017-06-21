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


def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


@mock.patch('cnxarchive.views.extras.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
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

    def test_get_extra_404(self):
        id = '94919e72-7573-4ed4-828e-673c1fe0cf9b'
        version = '66.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ...views.extras import get_extra

        with self.assertRaises(httpexceptions.HTTPNotFound) as caught_exc:
            response = get_extra(self.request)

    def test_get_extra_no_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ...views.extras import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'downloads': [{
                u'created': None,
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'college-physics-6.1.pdf',
                u'format': u'PDF',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.pdf/college-physics-6.1.pdf'),
                u'size': 0,
                u'state': u'missing'},
               {
                u'created': None,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'college-physics-6.1.epub',
                u'format': u'EPUB',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.epub/college-physics-6.1.epub'),
                u'size': 0,
                u'state': u'missing'},
               {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'college-physics-6.1.zip',
                u'format': u'Offline ZIP',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.zip/college-physics-6.1.zip'),
                u'size': 0,
                u'state': u'missing'}],
            u'isLatest': False,
            u'canPublish': [
                u'OpenStaxCollege',
                u'cnxcap',
                ],
            })

    def test_get_extra_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ...views.extras import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'PDF',
                u'size': 28,
                u'state': u'good',
                u'filename': u'college-physics-{}.pdf'.format(version),
                u'details': u'PDF file, for viewing content offline and printing.',
                u'path': quote(u'/exports/{}@{}.pdf/college-physics-{}.pdf'.format(
                    id, version, version)),
                },
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'EPUB',
                u'size': 13,
                u'state': u'good',
                u'filename': u'college-physics-{}.epub'.format(version),
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'path': quote(u'/exports/{}@{}.epub/college-physics-{}.epub'.format(
                    id, version, version)),
                },
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'Offline ZIP',
                u'size': 11,
                u'state': u'good',
                u'filename': u'college-physics-{}.zip'.format(version),
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'path': quote(u'/exports/{}@{}.zip/college-physics-{}.zip'.format(
                    id, version, version)),
                },
            ])

    def test_extra_downloads_with_legacy_filenames(self):
        # Tests for finding legacy filenames after a module is published from
        # the legacy site
        id = '209deb1f-1a46-4369-9e0d-18674cf58a3e'  # m42955
        version = '7'  # legacy_version: 1.7
        requested_ident_hash = '{}@{}'.format(id, version)

        # Remove the generated files after the test
        def remove_generated_files():
            file_glob = glob.glob('{}/exports2/{}@{}.*'.format(testing.DATA_DIRECTORY,
                                                               id, version))
            for f in file_glob:
                os.unlink(f)
        self.addCleanup(remove_generated_files)

        # Build the request
        self.request.matchdict = {'ident_hash': requested_ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ...views.extras import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                u'path': quote(u'/exports/{}@{}.pdf/preface-to-college-physics-7.pdf'
                               .format(id, version)),
                u'format': u'PDF',
                u'created': u'2015-03-04T10:03:29-08:00',
                u'state': u'good',
                u'size': 15,
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'preface-to-college-physics-7.pdf',
                },
            {
                u'path': quote(u'/exports/{}@{}.epub/preface-to-college-physics-7.epub'
                               .format(id, version)),
                u'format': u'EPUB',
                u'created': u'2015-03-04T10:03:29-08:00',
                u'state': u'good',
                u'size': 16,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'preface-to-college-physics-7.epub',
                },
            {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'preface-to-college-physics-7.zip',
                u'format': u'Offline ZIP',
                u'path': quote(u'/exports/209deb1f-1a46-4369-9e0d-18674cf58a3e@7.zip/preface-to-college-physics-7.zip'),
                u'size': 0,
                u'state': u'missing'}
            ])

    def test_extra_latest(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ...views.extras import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['isLatest'], True)

        version = '6.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        from ...views.extras import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['isLatest'], False)

    def test_extra_wo_version(self):
        # Request the extras for a document, but without specifying
        #   the version. The expectation is that this will redirect to the
        #   latest version.
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        requested_ident_hash = id
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': requested_ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ...views.extras import get_extra
        with self.assertRaises(IdentHashMissingVersion) as raiser:
            get_extra(self.request)

    def test_extra_shortid(self):
        # Request the extras for a document with a shortid and
        #   version. The expectation is that this will redirect to the
        #   fullid (uuid@version)

        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        from ...utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()
        version = '7.1'
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {
            'ident_hash': "{}@{}".format(short_id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ...views.extras import get_extra
        with self.assertRaises(IdentHashShortId) as raiser:
            get_extra(self.request)

    def test_extra_shortid_wo_version(self):
        # Request the extras for a document with a shortid and no
        #   version. The expectation is that this will redirect to the
        #   fullid (uuid@version)

        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ...utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': short_id}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ...views.extras import get_extra
        with self.assertRaises(IdentHashShortId) as raiser:
            get_extra(self.request)

    def test_extra_w_utf8_characters(self):
        id = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = '5'
        ident_hash = '{}@{}'.format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ...views.extras import get_extra
        output = get_extra(self.request).json_body
        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'canPublish': [
                u'OpenStaxCollege',
                u'cnxcap',
                ],
            u'isLatest': True,
            u'downloads': [{
                u'created': u'2015-03-04T10:03:29-08:00',
                u'path': quote('/exports/{}@{}.pdf/useful-inførmation-5.pdf'
                               .format(id, version)),
                u'format': u'PDF',
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'useful-inførmation-5.pdf',
                u'size': 0,
                u'state': u'good'},
                {
                u'created': None,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'useful-inf\xf8rmation-5.epub',
                u'format': u'EPUB',
                u'path': quote('/exports/{}@{}.epub/useful-inførmation-5.epub'
                               .format(id, version)),
                u'size': 0,
                u'state': u'missing'},
                {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'useful-inf\xf8rmation-5.zip',
                u'format': u'Offline ZIP',
                u'path': quote('/exports/{}@{}.zip/useful-inførmation-5.zip'
                               .format(id, version)),
                u'size': 0,
                u'state': u'missing'}],
            })

    def test_extra_not_found(self):
        # Test version not found
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ...views.extras import get_extra
        self.assertRaises(httpexceptions.HTTPNotFound, get_extra,
                          self.request)

        # Test id not found
        id = 'c694e5cc-47bd-41a4-b319-030647d93440'
        version = '1.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        self.assertRaises(httpexceptions.HTTPNotFound, get_extra,
                          self.request)

    @testing.db_connect
    def test_extras(self, cursor):
        # Setup a few service state messages.
        cursor.execute("""\
INSERT INTO service_state_messages
  (service_state_id, starts, ends, priority, message)
VALUES
  (1, CURRENT_TIMESTAMP + INTERVAL '3 hours',
   CURRENT_TIMESTAMP + INTERVAL '24 hours',
   NULL, NULL),
  (2, DEFAULT, DEFAULT, 8,
   'We have free books at free prices! Don''t miss out!'),
  (2, CURRENT_TIMESTAMP - INTERVAL '24 hours',
   CURRENT_TIMESTAMP - INTERVAL '2 hours',
   1, 'should not show up in the results.')""")
        cursor.connection.commit()

        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'extras'

        # Call the view
        from ...views.extras import extras
        metadata = extras(self.request).json_body
        messages = metadata.pop('messages')
        self.assertEqual(metadata, {
            u'subjects': [{u'id': 1, u'name': u'Arts',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 2, u'name': u'Business',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 3, u'name': u'Humanities',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 4, u'name': u'Mathematics and Statistics',
                           u'count': {u'module': 7, u'collection': 1},
                           },
                          {u'id': 5, u'name': u'Science and Technology',
                           u'count': {u'module': 6, u'collection': 1},
                           },
                          {u'id': 6, u'name': u'Social Sciences',
                           u'count': {u'module': 0, u'collection': 0},
                           }],
            u'featuredLinks': [{
                u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
                u'title': u'College Physics',
                u'version': u'7.1',
                u'legacy_id': u'col11406',
                u'legacy_version': u'1.7',
                u'resourcePath': u'/resources/6214e8dcdf2824dbf830b4a0d77a3fa2f53608d2',
                u'type': u'OpenStax Featured',
                u'abstract': u"""<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" \
xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">\
This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. \
This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics \
application problems.</div>""",
                }],
            u'languages_and_count': [[u'da', 1], [u'en', 17]],
            u'licenses': [{u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nd',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs License',
                           u'url': u'http://creativecommons.org/licenses/by-nd/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nd-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nd-nc/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nc/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-sa',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-sa/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/2.0/',
                           u'version': u'2.0'},
                          {u'code': u'by-nd',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs License',
                           u'url': u'http://creativecommons.org/licenses/by-nd/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-nd-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nd-nc/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nc/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-sa',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-sa/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/3.0/',
                           u'version': u'3.0'},
                          {u'code': u'by',
                           u'isValidForPublication': True,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/4.0/',
                           u'version': u'4.0'},
                          {u'code': u'by-nc-sa',
                           u'isValidForPublication': True,
                           u'name': u'Creative Commons Attribution-NonCommercial-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-nc-sa/4.0/',
                           u'version': u'4.0'}],
            })
