# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import shutil
import tempfile
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing

from ...utils import IdentHashMissingVersion
from .. import testing


TYPE_INFO = [
    ('pdf',
     {'description': 'PDF file, for viewing content offline and printing.',
      'file_extension': 'pdf',
      'mimetype': 'application/pdf',
      'user_friendly_name': 'PDF'}),
    ('zip',
     {'description': 'An offline HTML copy of the content.  Also includes XML, '
      'included media files, and other support files.',
      'file_extension': 'zip',
      'mimetype': 'application/zip',
      'user_friendly_name': 'Offline ZIP'}),
]


class GetExportFileTestCase(unittest.TestCase):

    def target(self, cursor, id, version, type, exports_dirs, read_file=True):
        from cnxarchive.views.exports import get_export_files
        return get_export_files(cursor, id, version, [type],
                                exports_dirs, read_file)[0]

    def setUp(self):
        self._mock_get_content_metadata()
        self._mock_fromtimestamp()
        self._setup_pyramid_app()

        self.cursor = None  # No need for a real cursor

    def _setup_pyramid_app(self):
        # Setup some faux export directories
        self.export_dirs = []
        for i in range(0, 2):
            dir = tempfile.mkdtemp()
            self.export_dirs.append(dir)
            self.addCleanup(shutil.rmtree, dir)

        request = pyramid_testing.DummyRequest()
        settings = {
            '_type_info': TYPE_INFO,
            'exports-directories': ' '.join(self.export_dirs),
        }
        config = pyramid_testing.setUp(
            request=request,
            settings=settings,
        )
        self.addCleanup(pyramid_testing.tearDown)

    def _mock_get_content_metadata(self):
        self.legacy_id = 'm55321'
        self.legacy_version = '1.4'
        self.legacy_title = 'The kittens and their mittens'
        self.mediaType = 'application/vnd.org.cnx.module'

        metadata = {
            'legacy_id': self.legacy_id,
            'legacy_version': self.legacy_version,
            'title': self.legacy_title,
            'mediaType': self.mediaType,
        }

        def get_content_metadata(id, version, cursor):
            return metadata

        patch = mock.patch(
            'cnxarchive.views.exports.get_content_metadata',
            get_content_metadata)
        patch.start()

        self.addCleanup(patch.stop)

    def _mock_fromtimestamp(self):

        def fromtimestamp(stamp):
            return '<datetime>'

        patch = mock.patch(
            'cnxarchive.views.exports.fromtimestamp',
            fromtimestamp)
        patch.start()

        self.addCleanup(patch.stop)

    def test_for_exporterror_on_invalid_type(self):
        from cnxarchive.views.exports import ExportError
        with self.assertRaises(ExportError) as caught_exception:
            self.target(self.cursor, '<id>', '<version>', 'book',
                        self.export_dirs)

        exc = caught_exception.exception
        self.assertEqual(exc.args, ("invalid type 'book' requested.",))

    def test_found_export(self):
        # Create the export file
        id, version = '<id>', '<version>'
        filename = '{}@{}.zip'.format(id, version)
        filepath = os.path.join(self.export_dirs[-1], filename)
        file_content = 'mittens'
        with open(filepath, 'w') as fb:
            fb.write(file_content)

        # Test the target function
        export_file_info = self.target(
            self.cursor,
            id,
            version,
            'zip',
            self.export_dirs,
        )

        # Check the results
        title, mimetype, size, time, state, content = export_file_info
        self.assertEqual(
            title,
            u'the-kittens-and-their-mittens-<version>.zip')
        self.assertEqual(mimetype, 'application/zip')
        self.assertEqual(size, 7)
        self.assertEqual(time, '<datetime>')
        self.assertEqual(state, 'good')
        self.assertEqual(content, file_content)

    def test_found_legacy_export(self):
        # Create the export file
        id, version = '<id>', '<version>'
        filename = '{}-{}.complete.zip'.format(self.legacy_id,
                                               self.legacy_version)
        filepath = os.path.join(self.export_dirs[-1], filename)
        file_content = 'mittens'
        with open(filepath, 'w') as fb:
            fb.write(file_content)

        # Test the target function
        export_file_info = self.target(
            self.cursor,
            id,
            version,
            'zip',
            self.export_dirs,
        )

        # Check the results
        title, mimetype, size, time, state, content = export_file_info
        self.assertEqual(
            title,
            u'the-kittens-and-their-mittens-<version>.zip')
        self.assertEqual(mimetype, 'application/zip')
        self.assertEqual(size, 7)
        self.assertEqual(time, '<datetime>')
        self.assertEqual(state, 'good')
        self.assertEqual(content, file_content)

    def test_for_file_not_found(self):
        # Patch the logger to capture the message call.
        mock_logger = mock.MagicMock()
        patch = mock.patch('cnxarchive.views.exports.logger', mock_logger)
        patch.start()
        self.addCleanup(patch.stop)

        id, version = '<id>', '<version>'

        # Test the target function
        export_file_info = self.target(
            self.cursor,
            id,
            version,
            'zip',
            self.export_dirs,
        )

        # Check the results
        title, mimetype, size, time, state, content = export_file_info
        self.assertEqual(
            title,
            u'the-kittens-and-their-mittens-<version>.zip')
        self.assertEqual(mimetype, 'application/zip')
        self.assertEqual(size, 0)
        self.assertEqual(time, None)
        self.assertEqual(state, 'missing')
        self.assertEqual(content, None)

        # Check the log message
        self.assertTrue(mock_logger.error.called)
        mock_logger.error.assert_called_with(
            "Could not find a file for '<id>' at version '<version>' "
            "with any of the following file names:\n"
            " - <id>@<version>.zip\n"
            " - m55321-1.4.complete.zip\n"
            " - m55321-1.4.zip")

    # https://github.com/Connexions/cnx-archive/issues/420
    def test_finding_file_with_multiple_suffix(self):
        # Create the export file
        id, version = '<id>', '<version>'
        filename = '{}-{}.zip'.format(self.legacy_id,
                                      self.legacy_version)
        filepath = os.path.join(self.export_dirs[-1], filename)
        file_content = 'not a .complete.zip, only a .zip'
        with open(filepath, 'w') as fb:
            fb.write(file_content)

        # Test the target function
        export_file_info = self.target(
            self.cursor,
            id,
            version,
            'zip',
            self.export_dirs,
        )

        # Check the results
        title, mimetype, size, time, state, content = export_file_info
        self.assertEqual(
            title,
            u'the-kittens-and-their-mittens-<version>.zip')
        self.assertEqual(mimetype, 'application/zip')
        self.assertEqual(size, 32)
        self.assertEqual(time, '<datetime>')
        self.assertEqual(state, 'good')
        self.assertEqual(content, file_content)


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
        type = 'zip'
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
                         "attachment; filename=college-physics-{ver}.zip;"
                         " filename*=UTF-8''college-physics-{ver}.zip"
                         .format(ver=version))
        self.assertEqual(self.request.response.headers['Link'],
                         '<https://example.com:80/contents/{id}'
                         '/college-physics> ;rel="Canonical"'
                         .format(id=id))

        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports',
                                     filename)
        with open(expected_file, 'r') as file:
            self.assertEqual(export, file.read())

        # Test unicode filename
        id = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = '5'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}@{}.zip'.format(id, version)
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': 'zip'
                                  }

        export = get_export(self.request).body
        self.assertEqual(
            self.request.response.content_disposition,
            "attachment; filename=useful-inf%C3%B8rmation-{ver}.zip;"
            " filename*=UTF-8''useful-inf%C3%B8rmation-{ver}.zip"
            .format(ver=version))

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}@{}.zip'.format(id, version)
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': 'zip'
                                  }

        export = get_export(self.request).body
        self.assertEqual(
            self.request.response.content_disposition,
            "attachment; filename=elasticity-stress-and-strain-{ver}.zip;"
            " filename*=UTF-8''elasticity-stress-and-strain-{ver}.zip"
            .format(ver=version))

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
                'type': 'zip'
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
