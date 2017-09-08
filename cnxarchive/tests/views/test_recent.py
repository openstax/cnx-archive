# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing

from .. import testing


class RecentViewsTestCase(unittest.TestCase):
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

    def test_format_author(self):
        from ...views.recent import format_author
        self.assertEqual(
            format_author(['cnxcap', 'OpenStaxCollege'], self.settings),
            'OSC Physics Maintainer, OpenStax Cöllege')

    def test_recent_rss(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'recent'
        self.request.GET = {'number': 5, 'start': 3, 'type': 'Module'}

        from ...views.recent import recent
        recent = recent(self.request)
        self.assertEqual(len(recent['latest_modules']), 5)
        # check that they are in correct order
        dates = []
        for module in recent['latest_modules']:
            dates.append(module["revised"].split(',')[1])
            keys = module.keys()
            keys.sort()
            self.assertEqual(keys, ["abstract", "authors", "name",
                                    "revised", "uuid"])
        dates_sorted = list(dates)
        dates_sorted.sort(reverse=True)
        self.assertEqual(dates_sorted, dates)


class RecentRssTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test(self):
        resp = self.testapp.get('/feeds/recent.rss')
        with open(os.path.join(testing.here, 'data/recent.rss')) as f:
            recent_rss = f.read()
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.body, recent_rss)
