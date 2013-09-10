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
import uuid
from wsgiref.util import setup_testing_defaults

import psycopg2
from paste.deploy import appconfig

from . import httpexceptions
from .database import CONNECTION_SETTINGS_KEY


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
    u'googleAnalytics': u'UA-XXXXX-Y',
    u'buyLink': None,
    }
COLLECTION_JSON_TREE = {
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@1.7',
    u'title': u'College Physics',
    u'contents': [
        {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@1.7',
         u'title': u'Preface'},
        {u'id': u'subcol',
         u'title': u'Introduction: The Nature of Science and Physics',
         u'contents': [
                {u'id': u'f3c9ab70-a916-4d8c-9256-42953287b4e9@1.3',
                 u'title': u'Introduction to Science and the Realm of Physics, Physical Quantities, and Units'},
                {u'id': u'd395b566-5fe3-4428-bcb2-19016e3aa3ce@1.4',
                 u'title': u'Physics: An Introduction'},
                {u'id': u'c8bdbabc-62b1-4a5f-b291-982ab25756d7@1.6',
                 u'title': u'Physical Quantities and Units'},
                {u'id': u'5152cea8-829a-4aaf-bcc5-c58a416ecb66@1.7',
                 u'title': u'Accuracy, Precision, and Significant Figures'},
                {u'id': u'5838b105-41cd-4c3d-a957-3ac004a48af3@1.5',
                 u'title': u'Approximation'},
                ],
         },
        {u'id': u'subcol',
         u'title': u"Further Applications of Newton's Laws: Friction, Drag, and Elasticity",
         u'contents': [
                {u'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@1.2',
                 u'title': u'Introduction: Further Applications of Newton\u2019s Laws'},
                {u'id': u'ea271306-f7f2-46ac-b2ec-1d80ff186a59@1.5',
                 u'title': u'Friction'},
                {u'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@1.6',
                 u'title': u'Drag Forces'},
                {u'id': u'56f1c5c1-4014-450d-a477-2121e276beca@1.8',
                 u'title': u'Elasticity: Stress and Strain'},
                ],
         },
        {u'id': u'f6024d8a-1868-44c7-ab65-45419ef54881@1.3',
         u'title': u'Atomic Masses'},
        {u'id': u'7250386b-14a7-41a2-b8bf-9e9ab872f0dc@1.2',
         u'title': u'Selected Radioactive Isotopes'},
        {u'id': u'c0a76659-c311-405f-9a99-15c71af39325@1.5',
         u'title': u'Useful Information'},
        {u'id': u'ae3e18de-638d-4738-b804-dc69cd4db3a3@1.4',
         u'title': u'Glossary of Key Symbols and Notation'},
        ],
    }
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
    u'googleAnalytics': None,
    u'buyLink': u'http://openstaxcollege.worksmartsuite.com/',
    }

SEARCH_RESULTS_1 = {
        u'query': {
            u'limits': [
                {u'text': u'college physics'},
                ],
            u'sort': [u'version'],
            },
        u'results': {
            u'total': 2,
            u'items': [
                {
                    u'id': u'b1509954-7460-43a4-8c52-262f1ddd7f2f',
                    u'type': u'book',
                    u'title': u'College Physics',
                    u'authors': [],
                    u'keywords': [],
                    u'summarySnippet': None,
                    u'bodySnippet': None,
                    u'pubDate': u'2013-08-13T12:12Z',
                    },
                {
                    u'id': u'85baef5b-acd6-446e-99bf-f2204caa25bc',
                    u'type': u'page',
                    u'title': u'Preface to College Physics',
                    u'authors': [],
                    u'keywords': [],
                    u'summarySnippet': None,
                    u'bodySnippet': None,
                    u'pubDate': u'2013-08-13T12:12Z',
                    },
                ],
            },
        }


class MockDBQuery(object):

    def __init__(self, query):
        self.filters = [q for q in query if q[0] == 'type']
        self.sorts = [q[1] for q in query if q[0] == 'sort']
        self.query = [q for q in query
                      if q not in self.filters and q[0] != 'sort']

    def __call__(self):
        if MockDBQuery.result_set == 1:
            return [
                    ('College Physics', 'College Physics', 'b1509954-7460-43a4-8c52-262f1ddd7f2f', '1.7', 'en', 111L, 'college physics-::-abstract;--;college physics-::-title;--;college physics-::-title', '', '', 'Collection'),
                    ('Preface to College Physics', 'Preface to College Physics', '85baef5b-acd6-446e-99bf-f2204caa25bc', '1.7', 'en', 110L, 'college physics-::-title;--;college physics-::-title', '', '', 'Module')
                    ]


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


class DBQueryTestCase(unittest.TestCase):
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
            cnxuser_schema_filepath = os.path.join(TEST_DATA,
                                                   'cnx-user.schema.sql')
            cnxuser_data_filepath = os.path.join(TEST_DATA,
                                                 'cnx-user.data.sql')
            with open(cnxuser_schema_filepath, 'r') as fb:
                cursor.execute(fb.read())
            with open(cnxuser_data_filepath, 'r') as fb:
                cursor.execute(fb.read())
            # FIXME This is a temporary fix until the data can be updated.
            cursor.execute("update modules set (authors, maintainers, licensors) = ('{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}');")
            cursor.execute("update latest_modules set (authors, maintainers, licensors) = ('{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}');")
        self._db_connection.commit()

    def tearDown(self):
        from . import _set_settings
        _set_settings(None)
        self.fixture.tearDown()

    def make_one(self, *args, **kwargs):
        # Single point of import failure.
        from .search import DBQuery
        return DBQuery(*args, **kwargs)

    def test_title_search(self):
        # Simple case to test for results of a basic title search.
        query_params = [('title', 'Physics')]
        db_query = self.make_one(query_params)
        results = db_query()

        self.assertEqual(len(results), 4)

    def test_abstract_search(self):
        # Test for result on an abstract search.
        query_params = [('abstract', 'algebra')]
        db_query = self.make_one(query_params)
        results = db_query()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][6], 'algebra-::-abstract')

    def test_author_search(self):
        # Test the results of an author search.
        user_id = str(uuid.uuid4())
        query_params = [('author', 'Jill')]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as an author.
                cursor.execute(
                    "UPDATE latest_modules SET (authors) = (%s) "
                    "WHERE uuid = %s::uuid OR uuid = %s::uuid;",
                    ([user_id], 'bdf58c1d-c738-478b-aea3-0c00df8f617c',
                     'bf8c0d8f-1255-47eb-9f17-83705ae4b16f',))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_editor_search(self):
        # Test the results of an editor search.
        user_id = str(uuid.uuid4())
        query_params = [('editor', 'jmiller@example.com')]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as an editor.
                role_id = 5
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 2, role_id))
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 3, role_id))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_licensor_search(self):
        # Test the results of a licensor search.
        user_id = str(uuid.uuid4())
        query_params = [('licensor', 'jmiller')]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as a licensor.
                role_id = 2
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 2, role_id))
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 3, role_id))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_maintainer_search(self):
        # Test the results of a maintainer search.
        user_id = str(uuid.uuid4())
        query_params = [('maintainer', 'Miller')]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as a maintainer.
                cursor.execute(
                    "UPDATE latest_modules SET (maintainers) = (%s) "
                    "WHERE uuid = %s::uuid OR uuid = %s::uuid;",
                    ([user_id], 'bdf58c1d-c738-478b-aea3-0c00df8f617c',
                     'bf8c0d8f-1255-47eb-9f17-83705ae4b16f',))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_translator_search(self):
        # Test the results of a translator search.
        user_id = str(uuid.uuid4())
        query_params = [('translator', 'jmiller')]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as a translator.
                role_id = 4
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 2, role_id))
                cursor.execute(
                    "INSERT INTO moduleoptionalroles"
                    "(personids, module_ident, roleid) VALUES (%s, %s, %s);",
                    ([user_id], 3, role_id))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_parentauthor_search(self):
        # Test the results of a parent author search.
        user_id = str(uuid.uuid4())
        # FIXME parentauthor is only searchable by user id, not by name
        #       like the other user based columns. Inconsistent behavior...
        query_params = [('parentauthor', user_id)]
        db_query = self.make_one(query_params)

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Create a new user.
                cursor.execute(
                    "INSERT INTO users "
                    "(id, firstname, surname, fullname, email) "
                    "VALUES (%s, %s, %s, %s, %s);",
                    (user_id, 'Jill', 'Miller', 'Jill M.',
                     'jmiller@example.com',))
                # Update two modules in include this user as a parent author.
                cursor.execute(
                    "UPDATE latest_modules SET (parentauthors) = (%s) "
                    "WHERE uuid = %s::uuid OR uuid = %s::uuid;",
                    ([user_id], 'bdf58c1d-c738-478b-aea3-0c00df8f617c',
                     'bf8c0d8f-1255-47eb-9f17-83705ae4b16f',))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 2)

    def test_type_filter_on_books(self):
        # Test for type filtering that will find books only.
        query_params = [('text', 'physics'), ('type', 'book')]
        db_query = self.make_one(query_params)

        results = db_query()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2],
                         'b1509954-7460-43a4-8c52-262f1ddd7f2f')

    def test_sort_filter_on_pubdate(self):
        # Test the sorting of results by publication date.
        query_params = [('text', 'physics'), ('sort', 'pubDate')]
        db_query = self.make_one(query_params)
        _same_date = '2113-01-01 00:00:00 America/New_York'
        expectations = [('e3f8051d-7fde-4f14-92f6-7f31019887b3',
                         _same_date,),  # this one has a higher weight.
                        ('bdf58c1d-c738-478b-aea3-0c00df8f617c',
                         _same_date,),
                        ('bf8c0d8f-1255-47eb-9f17-83705ae4b16f',
                         '2112-01-01 00:00:00 America/New_York',),
                        ]

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                # Update two modules in include a creation date.
                for id, date in expectations:
                    cursor.execute(
                        "UPDATE latest_modules SET (created) = (%s) "
                        "WHERE uuid = %s::uuid;", (date, id))
            db_connection.commit()

        results = db_query()
        self.assertEqual(len(results), 15)
        for i, (id, date) in enumerate(expectations):
            self.assertEqual(results[i][2], id)


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

        self.settings['exports-directories'] = ' '.join([
                os.path.join(TEST_DATA, 'exports'),
                os.path.join(TEST_DATA, 'exports2')
                ])
        self.settings['exports-allowable-types'] = '''
            pdf:pdf,application/pdf,Portable Document Format (PDF)
            epub:epub,application/epub+zip,Electronic Publication (EPUB)
            zip:zip,application/zip,ZIP archive
        '''

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
        self.assertEqual(content_tree, COLLECTION_JSON_TREE)

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
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.7'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        filename = "{}-{}.{}".format(id, version, type)

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
                         "attached; filename=college-physics.pdf")
        with open(os.path.join(TEST_DATA, 'exports', filename), 'r') as file:
            self.assertEqual(export, file.read())

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '1.8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}-{}.pdf'.format(id, version)
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash,
                                           'type': 'pdf'
                                           }

        export = get_export(environ, self._start_response)[0]
        headers = self.captured_response['headers']
        headers = {x[0].lower(): x[1] for x in headers}
        self.assertEqual(headers['content-disposition'],
                         "attached; filename=elasticity-stress-and-strain.pdf")
        with open(os.path.join(TEST_DATA, 'exports2', filename), 'r') as file:
            self.assertEqual(export, file.read())

    def test_exports_type_not_supported(self):
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
        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }

        from .views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                get_export, environ, self._start_response)

    def test_exports_without_version(self):
        id = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': id, 'type': 'pdf'}

        from .views import get_export
        get_export(environ, self._start_response)
        self.assertEqual(self.captured_response['status'], '302 Found')
        self.assertEqual(self.captured_response['headers'][0],
                ('Location', '/exports/{}@1.5.pdf'.format(id)))

    def test_get_exports_allowable_types(self):
        from .views import get_export_allowable_types
        output = get_export_allowable_types(self._make_environ,
                self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output), {
            'pdf': {
                'type_name': 'pdf',
                'file_extension': 'pdf',
                'mimetype': 'application/pdf',
                'user_friendly_name': 'Portable Document Format (PDF)',
                },
            'epub': {
                'type_name': 'epub',
                'file_extension': 'epub',
                'mimetype': 'application/epub+zip',
                'user_friendly_name': 'Electronic Publication (EPUB)',
                },
            'zip': {
                'type_name': 'zip',
                'file_extension': 'zip',
                'mimetype': 'application/zip',
                'user_friendly_name': 'ZIP archive',
                },
            })

    def test_search(self):
        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q="college physics" sort:version'

        # Mock DBQuery
        import views
        views.DBQuery = MockDBQuery
        MockDBQuery.result_set = 1

        from .views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)
        self.assertEqual(sorted(results.keys()), sorted(SEARCH_RESULTS_1.keys()))
        for i in results:
            self.assertEqual(results[i], SEARCH_RESULTS_1[i])


class SlugifyTestCase(unittest.TestCase):

    def test_ascii(self):
        from .utils import slugify
        self.assertEqual(slugify('How to Work for Yourself: 100 Ways'),
                'how-to-work-for-yourself-100-ways')

    def test_hyphen(self):
        from .utils import slugify
        self.assertEqual(slugify('Any Red-Blooded Girl'),
                'any-red-blooded-girl')

    def test_underscore(self):
        from .utils import slugify
        self.assertEqual(slugify('Underscores _hello_'),
                'underscores-_hello_')

    def test_unicode(self):
        from .utils import slugify
        self.assertEqual(slugify('Radioactive (Die Verstoßenen)'),
                u'radioactive-die-verstoßenen')

        self.assertEqual(slugify(u'40文字でわかる！'
            u'　知っておきたいビジネス理論'),
            u'40文字でわかる-知っておきたいビジネス理論')


class GetBuylinksTestCase(unittest.TestCase):
    """Tests for the get_buylinks script
    """

    fixture = postgresql_fixture

    def setUp(self):
        self.fixture.setUp()
        # Load the database with example legacy data.
        from .utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
            with db_connection.cursor() as cursor:
                with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
                    cursor.execute(fb.read())
        db_connection.commit()

        from .scripts import get_buylinks

        # Mock command line arguments:
        # arguments should be appended to self.argv by individual tests
        import argparse
        self.argv = ['cnx-archive_get_buylinks', TESTING_CONFIG]
        argparse._sys.argv = self.argv
        get_buylinks.argparse = argparse

        # Mock response from plone site:
        # responses should be assigned to self.responses by individual tests
        import StringIO
        import urllib2
        self.responses = ['']
        self.response_id = -1
        def urlopen(url):
            self.response_id += 1
            return StringIO.StringIO(self.responses[self.response_id])
        urllib2.urlopen = urlopen
        get_buylinks.urllib2 = urllib2

        # Use self.get_buylinks instead of importing it in tests to get all the
        # mocks
        self.get_buylinks = get_buylinks

    def tearDown(self):
        self.fixture.tearDown()

    def get_buylink_from_db(self, collection_id):
        from .utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(
                        'SELECT m.buylink FROM modules m WHERE m.moduleid = %(moduleid)s;',
                        {'moduleid': collection_id})
                return cursor.fetchone()[0]

    def test(self):
        self.argv.append('col11406')
        self.argv.append('m42955')
        self.responses = [
                # response for col11406
                "[('title', ''), "
                "('buyLink', 'http://buy-col11406.com/download')]",
                # response for m42955
                "[('title', ''), "
                "('buyLink', 'http://buy-m42955.com/')]"]
        self.get_buylinks.main()

        self.assertEqual(self.get_buylink_from_db('col11406'),
                'http://buy-col11406.com/download')
        self.assertEqual(self.get_buylink_from_db('m42955'),
                'http://buy-m42955.com/')

    def test_no_buylink(self):
        self.argv.append('m42955')
        self.response = "[('title', '')]"
        self.get_buylinks.main()

        self.assertEqual(self.get_buylink_from_db('m42955'), None)

    def test_collection_not_in_db(self):
        self.argv.append('col11522')
        self.response = ("[('title', ''), "
                "('buyLink', 'http://buy-col11522.com/download')]")
        # Just assert that the script does not fail
        self.get_buylinks.main()
