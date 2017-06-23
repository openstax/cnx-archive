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

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing

from .. import testing


class ResourcesViewsTestCase(unittest.TestCase):
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

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        hash = '075500ad9f71890a85fe3f7a4137ac08e2b7907c'

        # Build the request.
        self.request.matchdict = {'hash': hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'resource'

        # Call the view.
        from ...views.resource import get_resource
        resource = get_resource(self.request).body

        expected_bits = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xfe\x00\x00\x00\x93\x08\x06\x00\x00\x00\xf6\x90\x1d\x14'
        # Check the response body.
        self.assertEqual(bytes(resource)[:len(expected_bits)],
                         expected_bits)

        self.assertEqual(self.request.response.content_type, 'image/png')

    def test_resources_404(self):
        hash = 'invalid-hash'

        # Build the request
        self.request.matchdict = {'hash': hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'resource'

        # Call the view
        from ...views.resource import get_resource
        self.assertRaises(httpexceptions.HTTPNotFound, get_resource,
                          self.request)
