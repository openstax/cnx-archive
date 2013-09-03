# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import json
import unittest
from wsgiref.util import setup_testing_defaults

import psycopg2
from paste.deploy import appconfig

from . import httpexceptions


# Set the timezone for the postgresql client so that we get the times in the
# right timezone (America/Whitehorse is -07 in summer and -08 in winter)
os.environ['PGTZ'] = 'America/Whitehorse'

here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA = os.path.join(here, 'test-data')
TESTING_DATA_SQL_FILE = os.path.join(TEST_DATA, 'data.sql')
try:
    TESTING_CONFIG = os.environ['TESTING_CONFIG']
except KeyError as exc:
    print("*** Missing 'TESTING_CONFIG' environment variable ***")
    raise exc

COLLECTION_METADATA = {
    u'roles': None,
    u'subject': u'',
    u'abstract': u'This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics application problems.',
    u'authors': [],
    u'created': u'2013-07-31 12:07:20.342798-07',
    u'doctype': u'',
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [],
    u'maintainers': [],
    u'title': u'College Physics',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentVersion': None,
    u'revised': u'2013-07-31 12:07:20.342798-07',
    u'stateid': None,
    u'submitlog': u'',
    u'submitter': u'',
    u'mediaType': u'application/vnd.org.cnx.collection',
    u'version': u'1.7',
    }
COLLECTION_JSON_TREE = u'''{"id":"e79ffde3-7fb4-4af3-9ec8-df648b391597@1.7","title":"College Physics", "contents":[
    {"id":"209deb1f-1a46-4369-9e0d-18674cf58a3e@1.7","title":"Preface"},
    {"id":"subcol","title":"Introduction: The Nature of Science and Physics", "contents":[
        {"id":"f3c9ab70-a916-4d8c-9256-42953287b4e9@1.3","title":"Introduction to Science and the Realm of Physics, Physical Quantities, and Units"},
        {"id":"d395b566-5fe3-4428-bcb2-19016e3aa3ce@1.4","title":"Physics: An Introduction"},
        {"id":"c8bdbabc-62b1-4a5f-b291-982ab25756d7@1.6","title":"Physical Quantities and Units"},
        {"id":"5152cea8-829a-4aaf-bcc5-c58a416ecb66@1.7","title":"Accuracy, Precision, and Significant Figures"},
        {"id":"5838b105-41cd-4c3d-a957-3ac004a48af3@1.5","title":"Approximation"}]},
    {"id":"subcol","title":"Further Applications of Newton\'s Laws: Friction, Drag, and Elasticity", "contents":[
        {"id":"24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@1.2","title":"Introduction: Further Applications of Newton\\342\\200\\231s Laws"},
        {"id":"ea271306-f7f2-46ac-b2ec-1d80ff186a59@1.5","title":"Friction"},
        {"id":"26346a42-84b9-48ad-9f6a-62303c16ad41@1.6","title":"Drag Forces"},
        {"id":"56f1c5c1-4014-450d-a477-2121e276beca@1.8","title":"Elasticity: Stress and Strain"}]},
    {"id":"f6024d8a-1868-44c7-ab65-45419ef54881@1.3","title":"Atomic Masses"},
    {"id":"7250386b-14a7-41a2-b8bf-9e9ab872f0dc@1.2","title":"Selected Radioactive Isotopes"},
    {"id":"c0a76659-c311-405f-9a99-15c71af39325@1.5","title":"Useful Information"},
    {"id":"ae3e18de-638d-4738-b804-dc69cd4db3a3@1.4","title":"Glossary of Key Symbols and Notation"}]}'''
MODULE_METADATA = {
    u'roles': None,
    u'subject': u'',
    u'abstract': None,
    u'authors': [],
    u'created': u'2013-07-31 12:07:24.856663-07',
    u'doctype': u'',
    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [],
    u'maintainers': [],
    u'title': u'Elasticity: Stress and Strain',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentVersion': None,
    u'revised': u'2013-07-31 12:07:24.856663-07',
    u'stateid': None,
    u'submitlog': u'',
    u'submitter': u'',
    u'mediaType': u'application/vnd.org.cnx.module',
    u'version': u'1.8',
    }

def _get_app_settings(config_path):
    """Shortcut to the application settings. This does not load logging."""
    # This assumes the application is section is named 'main'.
    config_path = os.path.abspath(config_path)
    return appconfig("config:{}".format(config_path), name='main')


class SplitIdentTestCase(unittest.TestCase):

    def test_empty_value(self):
        # Case of supplying the utility function with an empty indent-hash.
        ident_hash = ''

        from .utils import split_ident_hash
        with self.assertRaises(ValueError):
            split_ident_hash(ident_hash)

    def test_complete_data(self):
        # Simple case of supplying the correct information and checking
        #   for the correct results.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '1.12',
            )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        from .utils import split_ident_hash
        id, version = split_ident_hash(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_uuid_only(self):
        # Case where the UUID has been the only value supplied in the
        #   ident-hash.
        # This is mostly testing that the version value returns None.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '',
            )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        from .utils import split_ident_hash
        id, version = split_ident_hash(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, None)

    def test_invalid_id(self):
        # Case for testing for an invalid identifier.
        ident_hash = "not-a-valid-id@"

        from .utils import split_ident_hash, IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            split_ident_hash(ident_hash)

    def test_invalid_syntax(self):
        # Case for testing the ident-hash's syntax guards.
        ident_hash = "85e57f7902b347d28eedc1bbb1e1d5c2@1.2@select*frommodules"

        from .utils import split_ident_hash, IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            split_ident_hash(ident_hash)


class RoutingTest(unittest.TestCase):

    def test_add_route_w_fq_import(self):
        # Check that a route can be added.
        from .views import get_content
        route_func = get_content
        path = "/contents/{ident_hash}"

        from . import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        self.assertEqual(controller, get_content)

    def test_add_route_w_import_str(self):
        # Check that a route can be added.
        route_func = 'cnxarchive.views:get_content'
        path = "/contents/{ident_hash}"

        from . import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        from .views import get_content
        self.assertEqual(controller, get_content)

    def test_route(self):
        # Check that we can route to a view, not that the route parses
        #   the path information.
        from . import Application
        app = Application()

        path_one = "/contents/{ident_hash}"
        view_one = 'cnxarchive.views:get_content'
        app.add_route(path_one, view_one)
        path_two = "/resources/{id}"
        view_two = 'cnxarchive.views:get_resource'
        app.add_route(path_two, view_two)

        id = '1a2b3c4d5678'
        environ = {'PATH_INFO': '/resources/{}'.format(id)}
        setup_testing_defaults(environ)
        controller = app.route(environ)

        from .views import get_resource
        self.assertEqual(controller, get_resource)
        self.assertEqual(environ['wsgiorg.routing_args'],
                         {'id': id})

class PostgresqlFixture:
    """A testing fixture for a live (same as production) SQL database.
    This will set up the database once for a test case. After each test
    case has completed, the database will be cleaned (all tables dropped).

    On a personal note, this seems archaic... Why can't I rollback to a
    transaction?
    """

    def __init__(self):
        # Configure the database connection.
        self._settings = _get_app_settings(TESTING_CONFIG)
        self._connection_string = self._settings['db-connection-string']
        # Drop all existing tables from the database.
        self._drop_all()

    def _drop_all(self):
        """Drop all tables in the database."""
        with psycopg2.connect(self._connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("CREATE SCHEMA public")

    def setUp(self):
        # Initialize the database schema.
        from .database import initdb
        initdb(self._settings)

    def tearDown(self):
        # Drop all tables.
        self._drop_all()

postgresql_fixture = PostgresqlFixture()


class ViewsTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        from .utils import parse_app_settings
        cls.settings = parse_app_settings(TESTING_CONFIG)
        from .database import CONNECTION_SETTINGS_KEY
        cls.db_connection_string = cls.settings[CONNECTION_SETTINGS_KEY]
        cls._db_connection = psycopg2.connect(cls.db_connection_string)

    @classmethod
    def tearDownClass(cls):
        cls._db_connection.close()

    def setUp(self):
        from . import _set_settings
        _set_settings(self.settings)
        self.fixture.setUp()
        # Load the database with example legacy data.
        with self._db_connection.cursor() as cursor:
            with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
                cursor.execute(fb.read())
        self._db_connection.commit()

    def tearDown(self):
        from . import _set_settings
        _set_settings(None)
        self.fixture.tearDown()

    def _make_environ(self):
        environ = {}
        setup_testing_defaults(environ)
        return environ

    def _start_response(self, status, headers=[]):
        """Used to capture the WSGI 'start_response'."""
        self.captured_response = {'status': status, 'headers': headers}

    def test_collection_content(self):
        # Test for retrieving a piece of content.
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.7'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from .views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(COLLECTION_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], COLLECTION_METADATA[key],
                    'content[{key}] = {v1} but COLLECTION_METADATA[{key}] = {v2}'.format(
                        key=key, v1=content[key], v2=COLLECTION_METADATA[key]))

        # Check the tree for accuracy.
        self.assertMultiLineEqual(content_tree, COLLECTION_JSON_TREE)

    def test_module_content(self):
        # Test for retreiving a module.
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '1.8'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from .views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

        # Remove the 'content' text from the content for separate testing.
        content_text = content.pop('content')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(MODULE_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], MODULE_METADATA[key],
                    'content[{key}] = {v1} but MODULE_METADATA[{key}] = {v2}'.format(
                        key=key, v1=content[key], v2=MODULE_METADATA[key]))

        # Check the content is the html file.
        self.assertTrue(content_text.find('<html') >= 0)

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        uuid = 'f45f8378-92db-40ae-ba58-648130038e4b'

        # Build the request.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'id': uuid}

        # Call the view.
        from .views import get_resource
        resource = get_resource(environ, self._start_response)[0]

        expected_bits = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xfe\x00\x00\x00\x93\x08\x06\x00\x00\x00\xf6\x90\x1d\x14'
        # Check the response body.
        self.assertEqual(bytes(resource)[:len(expected_bits)],
                         expected_bits)

        # Check for response headers, specifically the content-disposition.
        headers = self.captured_response['headers']
        expected_headers = [
            ('Content-type', 'image/png',),
            ('Content-disposition', "attached; filename=PhET_Icon.png",),
            ]
        self.assertEqual(headers, expected_headers)

    def test_exports(self):
        # Test for the retrieval of exports (e.g. pdf files).
        id = '8415caa0-2cf8-43d8-a073-05e41df8059c'
        version = '1.21'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        exports_dir = os.path.join(TEST_DATA, 'exports')
        filename = "{}-{}.{}".format(id, version, type)
        self.settings['exports-directory'] = exports_dir

        # Build the request.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash,
                                           'type': type,
                                           }

        from .views import get_export
        export = get_export(environ, self._start_response)[0]

        headers = self.captured_response['headers']
        headers = {x[0].lower(): x[1] for x in headers}
        self.assertEqual(headers['content-disposition'],
                         "attached; filename={}".format(filename))
        with open(os.path.join(exports_dir, filename), 'r') as file:
            self.assertEqual(export, file.read())

    def test_exports_type_not_supported(self):
        self.settings['exports-directories'] = ' '.join([
                os.path.join(TEST_DATA, 'exports'),
                os.path.join(TEST_DATA, 'exports2')
                ])

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {
                'ident_hash': '56f1c5c1-4014-450d-a477-2121e276beca@1.8',
                'type': 'txt'
                }

        from .views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                get_export, environ, self._start_response)

    def test_exports_404(self):
        self.settings['exports-directory'] = os.path.join(TEST_DATA, 'exports')

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }

        from .views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                get_export, environ, self._start_response)
