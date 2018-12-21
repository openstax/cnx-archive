# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2018, Rice University
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

import pretend
from pyramid import testing as pyramid_testing

from .. import testing


def stub_db_connect_database_interaction(results=[]):
    """Stub out the ``cnxarchive.database.db_connect`` function
    and child functions for simple interactions.

    The interactions look something like::

        >>> with db_connect() as db_conn:
        ...     with db_conn.cursor() as cursor:
        ...         cursor.execute(...)
        ...         results = cursor.fetchall()

    """
    # Stub the database interaction
    cursor = pretend.stub(
        execute=lambda *a, **kw: None,
        fetchall=lambda: results,
    )
    cursor_contextmanager = pretend.stub(
        __enter__=lambda *a: cursor,
        __exit__=lambda a, b, c: None,
    )
    db_conn = pretend.stub(cursor=lambda: cursor_contextmanager)
    db_connect_contextmanager = pretend.stub(
        __enter__=lambda: db_conn,
        __exit__=lambda a, b, c: None,
    )
    db_connect = pretend.stub(
        __call__=lambda: db_connect_contextmanager,
    )
    return db_connect


def monkeypatch_local_db_connect(test_case, new_func):
    # Monkeypatch the db_connect function
    from ...views import recent
    original_func = getattr(recent, 'db_connect')
    test_case.addCleanup(setattr, recent, 'db_connect', original_func)
    setattr(recent, 'db_connect', new_func)



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

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

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
            self.assertEqual(keys, [u"abstract", u"authors", u"name",
                                    u"revised", u"url"])
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
