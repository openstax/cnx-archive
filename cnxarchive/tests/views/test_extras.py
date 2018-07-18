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
from pyramid.encode import url_quote
from pyramid.traversal import PATH_SAFE

from .. import testing


def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


@mock.patch('cnxarchive.views.exports.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
class ExtrasViewsTestCase(unittest.TestCase):
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

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    def assert_featured_match(self, extras):
        self.assertEqual(extras['featured'], [
            {u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
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
application problems.</div>"""}
            ])

    def assert_messages_match(self, extras):
        messages = extras['messages']
        for message in messages:
            message.pop('starts')
            message.pop('ends')

        self.assertEqual(messages, [
            {u'message': u'This site is scheduled to be down for maintaince, please excuse the interuption. Thank you.',
             u'name': u'Maintenance',
             u'priority': 1},
            {u'message': u"We have free books at free prices! Don't miss out!",
             u'name': u'Notice',
             u'priority': 8}
            ])

    def assert_licenses_match(self, extras):
        self.assertEqual(extras['licenses'], [
            {u'code': u'by',
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
             u'version': u'4.0'}
            ])

    def assert_subjects_match(self, extras):
        self.assertEqual(extras['subjects'], [
            {u'id': 1, u'name': u'Arts',
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
             }
            ])

    def assert_languages_match(self, extras):
        self.assertEqual(extras['languages'], [[u'da', 1], [u'en', 19]])

    @testing.db_connect
    def test_extras(self, cursor):
        # Call the view
        from ...views.extras import extras
        metadata = extras(self.request).json_body
        self.assert_featured_match(metadata)
        self.assert_messages_match(metadata)
        self.assert_licenses_match(metadata)
        self.assert_subjects_match(metadata)
        self.assert_languages_match(metadata)

    @testing.db_connect
    def test_featured_links(self, cursor):
        # Call the view
        from ...views.extras import extras
        self.request.matchdict['key'] = 'featured'
        metadata = extras(self.request).json_body
        self.assertEqual(metadata.keys(), ['featured'])
        self.assert_featured_match(metadata)

    @testing.db_connect
    def test_messages(self, cursor):
        # Call the view
        from ...views.extras import extras
        self.request.matchdict['key'] = 'messages'
        metadata = extras(self.request).json_body
        self.assertEqual(metadata.keys(), ['messages'])
        self.assert_messages_match(metadata)

    @testing.db_connect
    def test_licenses(self, cursor):
        # Call the view
        from ...views.extras import extras
        self.request.matchdict['key'] = 'licenses'
        metadata = extras(self.request).json_body
        self.assertEqual(metadata.keys(), ['licenses'])
        self.assert_licenses_match(metadata)

    @testing.db_connect
    def test_subjects(self, cursor):
        # Call the view
        from ...views.extras import extras
        self.request.matchdict['key'] = 'subjects'
        metadata = extras(self.request).json_body
        self.assertEqual(metadata.keys(), ['subjects'])
        self.assert_subjects_match(metadata)

    @testing.db_connect
    def test_languages(self, cursor):
        # Call the view
        from ...views.extras import extras
        self.request.matchdict['key'] = 'languages'
        metadata = extras(self.request).json_body
        self.assertEqual(metadata.keys(), ['languages'])
        self.assert_languages_match(metadata)
