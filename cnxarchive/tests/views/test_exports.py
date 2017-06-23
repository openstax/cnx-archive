# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing

from ...utils import IdentHashMissingVersion
from .. import testing


@mock.patch('cnxarchive.views.exports.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
class ExportsViewsTestCase(unittest.TestCase):
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

    def test_exports(self):
        # Test for the retrieval of exports (e.g. pdf files).
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        filename = "{}@{}.{}".format(id, version, type)

        # Build the request.
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': type,
                                  }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ...views.exports import get_export
        export = get_export(self.request).body

        self.assertEqual(self.request.response.content_disposition,
                         "attached; filename=college-physics-{}.pdf"
                         .format(version))
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports',
                                     filename)
        with open(expected_file, 'r') as file:
            self.assertEqual(export, file.read())

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}@{}.pdf'.format(id, version)
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': 'pdf'
                                  }

        export = get_export(self.request).body
        self.assertEqual(
            self.request.response.content_disposition,
            "attached; filename=elasticity-stress-and-strain-{}.pdf"
            .format(version))

        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports2',
                                     filename)
        with open(expected_file, 'r') as file:
            self.assertEqual(export, file.read())

    def test_exports_type_not_supported(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '56f1c5c1-4014-450d-a477-2121e276beca@8',
                'type': 'txt'
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ...views.exports import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_404(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ...views.exports import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_without_version(self):
        id = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request
        self.request.matchdict = {'ident_hash': id, 'type': 'pdf'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ...views.exports import get_export
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_export(self.request)
