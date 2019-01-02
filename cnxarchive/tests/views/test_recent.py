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

import pretend
import pyramid.testing as pyramid_testing

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
    db_conn = pretend.stub(cursor=lambda **kw: cursor_contextmanager)
    db_connect_contextmanager = pretend.stub(
        __enter__=lambda: db_conn,
        __exit__=lambda a, b, c: None,
    )
    db_connect = pretend.stub(
        __call__=lambda: db_connect_contextmanager,
    )
    return db_connect


def monkeypatch(test_case, obj, attr, new):
    original = getattr(obj, attr)
    test_case.addCleanup(setattr, obj, attr, original)
    setattr(obj, attr, new)


def monkeypatch_local_db_connect(test_case, new_func):
    # Monkeypatch the db_connect function
    from ...views import recent
    monkeypatch(test_case, recent, 'db_connect', new_func)


class RecentRssViewTestCase(unittest.TestCase):

    def test(self):
        request = pyramid_testing.DummyRequest()
        request.matched_route = pretend.stub(name='recent')
        request.GET = {'number': 5, 'start': 3, 'type': 'Module'}
        request.response = pretend.stub()
        request.route_url = pretend.call_recorder(
            lambda n, ident_hash: n + ':' + ident_hash)

        # Stub the database interaction
        # FIXME: test for None abstract value
        row_info = [
            ('intro', '<feb>', 'john, wanda', None, 'id@1'),
            ('book', '<mar>', 'jen, sal, harry', '<abstract>', 'id@5.1'),
        ]
        row_keys = ['name', 'revised', 'authors', 'abstract', 'ident_hash']
        db_results = map(lambda x: dict(zip(row_keys, x)), row_info)
        db_connect = stub_db_connect_database_interaction(db_results)

        # Monkeypatch the dependency functions
        from ...views import recent
        monkeypatch(self, recent, 'db_connect', db_connect)
        monkeypatch(self, recent, 'rfc822', lambda x: 'rfc822:' + x)

        # Call the target
        from ...views.recent import recent
        recent = recent(request)

        self.assertEqual(len(recent['latest_modules']), 2)
        for i, module in enumerate(recent['latest_modules']):
            keys = module.keys()
            keys.sort()
            self.assertEqual(keys, [u"abstract", u"authors", u"name",
                                    u"revised", u"url"])
            expected = {
                u'name': row_info[i][0],
                u'revised': 'rfc822:' + row_info[i][1],
                u'authors': row_info[i][2],
                u'abstract': row_info[i][3],
                u'url': 'content:' + row_info[i][4],
            }
            self.assertEqual(expected, module)


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
