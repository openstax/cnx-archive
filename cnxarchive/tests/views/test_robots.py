# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import datetime
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing

from .. import testing


class RobotsViewsTestCase(unittest.TestCase):
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

    def test_robots(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'robots'

        # Call the view
        mocked_time = datetime.datetime(2015, 3, 4, 18, 3, 29)
        with mock.patch('cnxarchive.views.robots.datetime') as mock_datetime:
            def patched_now_side_effect(timezone):
                return timezone.localize(mocked_time)
            mock_datetime.now.side_effect = patched_now_side_effect
            from ...views.robots import robots
            robots = robots(self.request).body

        # Check the headers
        resp = self.request.response
        self.assertEqual(resp.content_type, 'text/plain')
        self.assertEqual(
            str(resp.cache_control), 'max-age=36000, must-revalidate')
        self.assertEqual(resp.headers['Last-Modified'],
                         'Wed, 04 Mar 2015 18:03:29 GMT')
        self.assertEqual(resp.headers['Expires'],
                         'Mon, 09 Mar 2015 18:03:29 GMT')

        # Check robots.txt content
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'robots.txt')
        with open(expected_file, 'r') as f:
            self.assertMultiLineEqual(robots, f.read())
