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


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA = os.path.join(here, 'test-data')
try:
    TESTING_CONFIG = os.environ['TESTING_CONFIG']
except KeyError as exc:
    print("*** Missing 'TESTING_CONFIG' environment variable ***")
    raise exc


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
        connection_string = cls.settings[CONNECTION_SETTINGS_KEY]
        cls.db_connection = psycopg2.connect(connection_string)

    @classmethod
    def tearDownClass(cls):
        cls.db_connection.close()

    def setUp(self):
        from . import _set_settings
        _set_settings(self.settings)
        self.fixture.setUp()

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

    def test_contents(self):
        # Test for retrieving a piece of content.
        # Insert an abstract and module.
        abstract_row = (1, "an abstract",)
        module_row = ('smoo', 1, '', abstract_row[0],)
        with self.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO abstracts (abstractid, abstract) "
                           "VALUES (%s, %s);", abstract_row)
            self.db_connection.commit()
            cursor.execute("INSERT INTO modules (name, licenseid, doctype, abstractid)"
                           "VALUES (%s, %s, %s, %s);", module_row)
            self.db_connection.commit()
            cursor.execute("SELECT uuid, version FROM modules;")
            uuid, version = cursor.fetchone()
        self.db_connection.commit()

        # Build the request environment.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': "{}@{}".format(uuid, version)}

        # Call the view.
        from .views import get_content
        content = get_content(environ, self._start_response)[0]

        content = json.loads(content)
        self.assertEqual(content['name'], module_row[0])
        self.assertEqual(content['abstract'], abstract_row[1])
        # FIXME This is all the farther we've got in the process of extracting
        #       the content.

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        # Insert a resource. In this case the resource does not need to
        #   be attatched to a module.
        file_row = (1, b'dingo-ate-my-baby')
        module_file_row = (file_row[0], 'image.jpg', 'image/jpeg')
        with self.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO files (fileid, file) VALUES (%s, %s);",
                           file_row)
            cursor.execute("INSERT INTO module_files (fileid, filename, mimetype) "
                           "VALUES (%s, %s, %s);", module_file_row)
            self.db_connection.commit()
            cursor.execute("SELECT uuid FROM module_files;")
            uuid = cursor.fetchone()[0]
        self.db_connection.commit()

        # Build the request.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'id': uuid}

        # Call the view.
        from .views import get_resource
        resource = get_resource(environ, self._start_response)[0]

        # Check the response body.
        self.assertEqual(bytes(resource), file_row[1])

        # Check for response headers, specifically the content-disposition.
        # self.fail()

    def test_exports(self):
        # Test for the retrieval of exports (e.g. pdf files).
        id = '8415caa0-2cf8-43d8-a073-05e41df8059c'
        version = '1.21'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        # Link up the exports directory, which is only done in dev-mode,
        #   because the web server will be doing this in production.
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
