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
from pyramid.encode import url_quote
from pyramid.traversal import PATH_SAFE

from .. import testing


def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


class LegacyRedirectViewsTestCase(unittest.TestCase):
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

    def test_legacy_id_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, latest version
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@5'.format(uuid)))

    def test_legacy_id_ver_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.5'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, latest version
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@5'.format(uuid)))

    # https://github.com/Connexions/cnx-archive/issues/452
    @testing.db_connect
    def test_legacy_id_old_ver_collection_with_missing_tree(self, cursor):
        book_uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        page_uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'
        colid = 'col15533'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.params = {'collection': '{}/latest'.format(colid)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Delete tree associated with this book.
        cursor.execute('DELETE FROM trees WHERE documentid = (SELECT module_ident FROM modules WHERE uuid = %s);', (book_uuid,))
        cursor.connection.commit()

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPNotFound) as cm:
            redirect_legacy_content(self.request)

    def test_legacy_id_old_ver_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@4'.format(uuid)))

    def test_legacy_bad_id_redirect(self):
        objid = 'foobar'

        # Build the request environment.
        self.request.matchdict = {'objid': objid}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPNotFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '404 Not Found')

    def test_legacy_id_old_ver_collection_context(self):
        book_uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        page_uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'
        colid = 'col15533'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.params = {'collection': '{}/latest'.format(colid)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(
            cm.exception.headers['Location'],
            quote('/contents/{}@1.1:{}'.format(book_uuid, page_uuid)))

    def test_legacy_id_old_ver_bad_collection_context(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.params = {'collection': 'col45555/latest'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@4'.format(uuid)))

    def test_legacy_filename_redirect(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        objid = 'm42081'
        objver = '1.8'
        filename = 'Figure_06_03_10a.jpg'
        sha1 = '95430b74a5ee9e09037c589feb0685ee226a06b8'

        # Build the request environment.
        self.request.matchdict = {'objid': objid,
                                  'objver': objver,
                                  'filename': filename}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view redirects to the resources url
        with self.assertRaises(httpexceptions.HTTPMovedPermanently) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '301 Moved Permanently')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/resources/{}/{}'.format(sha1, filename)))

    def test_legacy_no_such_filename_redirect(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        objid = 'm42081'
        objver = '1.8'
        filename = 'nothere.png'

        # Build the request environment.
        self.request.matchdict = {'objid': objid,
                                  'objver': objver,
                                  'filename': filename}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ...views.legacy_redirect import redirect_legacy_content

        # Check that the view 404s
        self.assertRaises(httpexceptions.HTTPNotFound,
                          redirect_legacy_content, self.request)
