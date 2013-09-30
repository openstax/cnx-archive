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
TEST_DATA_DIRECTORY = os.path.join(here, 'test-data')
TESTING_DATA_SQL_FILE = os.path.join(TEST_DATA_DIRECTORY, 'data.sql')
TESTING_CNXUSER_DATA_SQL_FILE = os.path.join(TEST_DATA_DIRECTORY, 'cnx-user.data.sql')
try:
    TESTING_CONFIG = os.environ['TESTING_CONFIG']
except KeyError as exc:
    print("*** Missing 'TESTING_CONFIG' environment variable ***")
    raise exc

COLLECTION_METADATA = {
    u'roles': None,
    u'subject': u'Mathematics and Statistics,Science and Technology',
    u'abstract': u'This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics application problems.',
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31 12:07:20.342798-07',
    u'doctype': u'',
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [{u'website': None, u'surname': u'University',
                    u'suffix': None, u'firstname': u'Rice',
                    u'title': None, u'othername': None,
                    u'id': u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                    u'fullname': u'Rice University',
                    u'email': u'daniel@openstaxcollege.org'},
                   ],
    u'maintainers': [{u'website': None, u'surname': u'Physics',
                      u'suffix': None, u'firstname': u'College',
                      u'title': None, u'othername': None,
                      u'id': u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                      u'fullname': u'OSC Physics Maintainer',
                      u'email': u'info@openstaxcollege.org'},
                     {u'website': None, u'surname': None,
                      u'suffix': None, u'firstname': u'OpenStax College',
                      u'title': None, u'othername': None,
                      u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                      u'fullname': u'OpenStax College',
                      u'email': u'info@openstaxcollege.org'},
                     ],
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
    u'subject': u'Science and Technology',
    u'abstract': None,
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31 12:07:24.856663-07',
    u'doctype': u'',
    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [{u'website': None, u'surname': u'University',
                    u'suffix': None, u'firstname': u'Rice',
                    u'title': None, u'othername': None,
                    u'id': u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                    u'fullname': u'Rice University',
                    u'email': u'daniel@openstaxcollege.org'},
                   ],
    u'maintainers': [{u'website': None, u'surname': u'Physics',
                      u'suffix': None, u'firstname': u'College',
                      u'title': None, u'othername': None,
                      u'id': u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                      u'fullname': u'OSC Physics Maintainer',
                      u'email': u'info@openstaxcollege.org'},
                     {u'website': None, u'surname': None,
                      u'suffix': None, u'firstname': u'OpenStax College',
                      u'title': None, u'othername': None,
                      u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                      u'fullname': u'OpenStax College',
                      u'email': u'info@openstaxcollege.org'},
                     ],
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

with open(os.path.join(TEST_DATA_DIRECTORY, 'raw-search-rows.json'), 'r') as fb:
    # Search results for a search on 'physics'.
    RAW_QUERY_RECORDS = json.load(fb)
SEARCH_RESULTS = {
    u'query': {
        u'limits': [{u'text': u'college physics'}],
        u'sort': [u'version'],
        },
    u'results': {
        u'items': [
            {u'authors': [{u'email': u'info@openstaxcollege.org',
                           u'firstname': u'OpenStax College',
                           u'fullname': u'OpenStax College',
                           u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                           u'othername': None,
                           u'suffix': None,
                           u'surname': None,
                           u'title': None,
                           u'website': None}],
             u'bodySnippet': None,
             u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
             u'keywords': [u'college physics',
                           u'physics',
                           u'friction',
                           u'ac circuits',
                           u'atomic physics',
                           u'bioelectricity',
                           u'biological and medical applications',
                           u'circuits',
                           u'collisions',
                           u'dc instruments',
                           u'drag',
                           u'elasticity',
                           u'electric charge and electric field',
                           u'electric current',
                           u'electric potential',
                           u'electrical technologies',
                           u'electromagnetic induction',
                           u'electromagnetic waves',
                           u'energy',
                           u'fluid dynamics',
                           u'fluid statics',
                           u'forces',
                           u'frontiers of physics',
                           u'gas laws',
                           u'geometric optics',
                           u'heat and transfer methods',
                           u'kinematics',
                           u'kinetic theory',
                           u'linear momentum',
                           u'magnetism',
                           u'medical applications of nuclear physics',
                           u'Newton\u2019s Laws of Motion',
                           u'Ohm\u2019s Law',
                           u'oscillatory motion and waves',
                           u'particle physics',
                           u'physics of hearing',
                           u'quantum physics',
                           u'radioactivity and nuclear physics',
                           u'resistance',
                           u'rotational motion and angular momentum',
                           u'special relativity',
                           u'statics and torque',
                           u'temperature',
                           u'thermodynamics',
                           u'uniform circular motion and gravitation',
                           u'vision and optical instruments',
                           u'wave optics',
                           u'work'],
             u'mediaType': u'Collection',
             u'pubDate': u'2013-07-31 12:07:20.342798-07',
             u'summarySnippet': u'algebra-based, two-semester <b>college</b> <b>physics</b> book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental <b>physics</b> concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional <b>physics</b> application problems.',
             u'title': u'College Physics'},
            {u'authors': [{u'email': u'info@openstaxcollege.org',
                           u'firstname': u'OpenStax College',
                           u'fullname': u'OpenStax College',
                           u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                           u'othername': None,
                           u'suffix': None,
                           u'surname': None,
                           u'title': None,
                           u'website': None}],
             u'bodySnippet': None,
             u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e',
             u'keywords': [u'college physics',
                           u'introduction',
                           u'physics'],
             u'mediaType': u'Module',
             u'pubDate': u'2013-07-31 12:07:20.542211-07',
             u'summarySnippet': None,
             u'title': u'Preface to College Physics'}],
        u'total': 2}}


def db_connect(method):
    """Decorator for methods that need to use the database

    Example:
    @db_connection
    def setUp(self, cursor):
        cursor.execute(some_sql)
        # some other code
    """
    def wrapped(self, *args, **kwargs):
        from .utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
            with db_connection.cursor() as cursor:
                return method(self, cursor, *args, **kwargs)
            db_connection.commit()
    return wrapped

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
    is_set_up = False

    def __init__(self):
        # Configure the database connection.
        self._settings = _get_app_settings(TESTING_CONFIG)
        self._connection_string = self._settings['db-connection-string']
        # Drop all existing tables from the database.
        self._drop_all()

    @db_connect
    def _drop_all(self, cursor):
        """Drop all tables in the database."""
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")

    def setUp(self):
        if self.is_set_up:
            # Failed to clean up after last use.
            self.tearDown()
        # Initialize the database schema.
        from .database import initdb
        initdb(self._settings)
        self.is_set_up = True

    def tearDown(self):
        # Drop all tables.
        self._drop_all()

postgresql_fixture = PostgresqlFixture()


class SearchModelTestCase(unittest.TestCase):
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
            with open(TESTING_CNXUSER_DATA_SQL_FILE, 'r') as fb:
                cursor.execute(fb.read())
        self._db_connection.commit()

    def tearDown(self):
        from . import _set_settings
        _set_settings(None)
        self.fixture.tearDown()

    def test_summary_highlighting(self):
        # Confirm the record highlights on found terms in the abstract/summary.
        from .search import QueryRecord
        record = QueryRecord(**RAW_QUERY_RECORDS[0][0])

        expected = """algebra-based, two-semester college <b>physics</b> book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental <b>physics</b> concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional <b>physics</b> application problems."""
        self.assertEqual(record.highlighted_abstract, expected)

    def test_fulltext_highlighting(self):
        # Confirm the record highlights on found terms in the fulltext.
        from .search import QueryRecord
        record = QueryRecord(**RAW_QUERY_RECORDS[0][0])

        expected = None
        # XXX Something wrong with the data, but otherwise this works as
        #     expected.
        self.assertEqual(record.highlighted_fulltext, expected)

    def test_result_counts(self):
        # Verify the counts on the results object.
        from .search import QueryResults
        results = QueryResults(RAW_QUERY_RECORDS)

        self.assertEqual(len(results), 15)
        # Check the mediaType counts.
        from .utils import MODULE_MIMETYPE, COLLECTION_MIMETYPE
        self.assertEqual(results.counts['mediaType'][MODULE_MIMETYPE], 14)
        self.assertEqual(results.counts['mediaType'][COLLECTION_MIMETYPE], 1)
        # Check the author counts
        self.assertEqual(results.counts['author'],
                         {u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8': 15})
        # Check counts for publication year.
        self.assertEqual(results.counts['pubYear'], {u'2013': 15})
        # Check the subject counts.
        self.assertEqual(results.counts['subject'],
                         {u'Mathematics and Statistics': 8,
                          u'Science and Technology': 7,
                          })
        # Check the keyword counts.
        self.assertEqual(results.counts['keyword']['Modern physics'], 2)
        self.assertEqual(results.counts['keyword']['particle physics'], 1)
        self.assertEqual(results.counts['keyword']['force'], 3)


class SearchTestCase(unittest.TestCase):
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
            with open(TESTING_CNXUSER_DATA_SQL_FILE, 'r') as fb:
                cursor.execute(fb.read())
        self._db_connection.commit()

    def tearDown(self):
        from . import _set_settings
        _set_settings(None)
        self.fixture.tearDown()

    def call_target(self, query_params):
        # Single point of import failure.
        from .search import search, Query
        query = Query(query_params)
        return search(query)

    def test_title_search(self):
        # Simple case to test for results of a basic title search.
        query_params = [('title', 'Physics')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 4)

    def test_abstract_search(self):
        # Test for result on an abstract search.
        query_params = [('abstract', 'algebra')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].fields['abstract'], set(['algebra']))

    def test_author_search(self):
        # Test the results of an author search.
        user_id = str(uuid.uuid4())
        query_params = [('author', 'Jill')]

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
                    "WHERE module_ident = %s OR module_ident = %s;",
                    ([user_id], 2, 3,))
            db_connection.commit()

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_editor_search(self):
        # Test the results of an editor search.
        user_id = str(uuid.uuid4())
        query_params = [('editor', 'jmiller@example.com')]

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

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_licensor_search(self):
        # Test the results of a licensor search.
        user_id = str(uuid.uuid4())
        query_params = [('licensor', 'jmiller')]

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

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_maintainer_search(self):
        # Test the results of a maintainer search.
        user_id = str(uuid.uuid4())
        query_params = [('maintainer', 'Miller')]

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
                    "WHERE module_ident = %s OR module_ident = %s;",
                    ([user_id], 2, 3,))
            db_connection.commit()

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_translator_search(self):
        # Test the results of a translator search.
        user_id = str(uuid.uuid4())
        query_params = [('translator', 'jmiller')]

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

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_parentauthor_search(self):
        # Test the results of a parent author search.
        user_id = str(uuid.uuid4())
        # FIXME parentauthor is only searchable by user id, not by name
        #       like the other user based columns. Inconsistent behavior...
        query_params = [('parentauthor', user_id)]

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
                    "WHERE module_ident = %s OR module_ident = %s;",
                    ([user_id], 2, 3,))
            db_connection.commit()

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_type_filter_on_books(self):
        # Test for type filtering that will find books only.
        query_params = [('text', 'physics'), ('type', 'book')]

        results = self.call_target(query_params)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'],
                         'e79ffde3-7fb4-4af3-9ec8-df648b391597')

    def test_sort_filter_on_pubdate(self):
        # Test the sorting of results by publication date.
        query_params = [('text', 'physics'), ('sort', 'pubDate')]
        _same_date = '2113-01-01 00:00:00 America/New_York'
        expectations = [('d395b566-5fe3-4428-bcb2-19016e3aa3ce',
                         _same_date,),  # this one has a higher weight.
                        ('c8bdbabc-62b1-4a5f-b291-982ab25756d7',
                         _same_date,),
                        ('5152cea8-829a-4aaf-bcc5-c58a416ecb66',
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

        results = self.call_target(query_params)
        self.assertEqual(len(results), 15)
        for i, (id, date) in enumerate(expectations):
            self.assertEqual(results[i]['id'], id)


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
            # Populate the cnx-user shadow.
            with open(TESTING_CNXUSER_DATA_SQL_FILE, 'r') as fb:
                cursor.execute(fb.read())
        self._db_connection.commit()

        self.settings['exports-directories'] = ' '.join([
                os.path.join(TEST_DATA_DIRECTORY, 'exports'),
                os.path.join(TEST_DATA_DIRECTORY, 'exports2')
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

    def test_content_without_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}".format(uuid)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from .views import get_content

        # Check that the view redirects to the latest version
        try:
            get_content(environ, self._start_response)
            self.assert_(False, 'should not get here')
        except httpexceptions.HTTPFound, e:
            self.assertEqual(e.status, '302 Found')
            self.assertEqual(e.headers, [('Location',
                '/contents/{}@1.5'.format(uuid))])

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
        with open(os.path.join(TEST_DATA_DIRECTORY, 'exports', filename), 'r') as file:
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
        with open(os.path.join(TEST_DATA_DIRECTORY, 'exports2', filename), 'r') as file:
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
        try:
            get_export(environ, self._start_response)
            self.assert_(False, 'should not get here')
        except httpexceptions.HTTPFound, e:
            self.assertEqual(e.status, '302 Found')
            self.assertEqual(e.headers, [('Location',
                '/exports/{}@1.5.pdf'.format(id))])

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

        from .views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(sorted(results.keys()), sorted(SEARCH_RESULTS.keys()))
        for i in results:
            self.assertEqual(results[i], SEARCH_RESULTS[i])


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

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

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

    @db_connect
    def get_buylink_from_db(self, cursor, collection_id):
        from .utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
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


class CORSTestCase(unittest.TestCase):
    """Tests for correctly enabling CORS on the server
    """

    def start_response(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def controller(self, environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return ['hello']

    def test_get(self):
        # We should have "Access-Control-Allow-Origin: *" in
        # the headers
        from . import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'GET',
                'PATH_INFO': '/',
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
            ]))
        self.assertEqual(self.kwargs, {})

    def test_options(self):
        # We should have "Access-Control-Allow-Origin: *" in the headers for
        # preflighted requests
        from . import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'OPTIONS',
                'PATH_INFO': '/',
                'HTTP_ACCESS_CONTROL_REQUEST_HEADERS':
                'origin, accept-encoding, accept-language, cache-control'
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
            ('Access-Control-Allow-Headers',
                'origin, accept-encoding, accept-language, cache-control'),
            ]))
        self.assertEqual(self.kwargs, {})

    def test_post(self):
        # We should not have "Access-Control-Allow-Origin: *" in
        # the headers
        from . import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'POST',
                'PATH_INFO': '/',
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ]))
        self.assertEqual(self.kwargs, {})


class ModulePublishTriggerTestCase(unittest.TestCase):
    """Tests for the postgresql triggers when a module is published
    """

    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def test_module(self, cursor):
        cursor.execute('SELECT nodeid FROM trees '
                'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        old_nodeid = cursor.fetchone()[0]

        cursor.execute('SELECT fileid '
                'FROM module_files WHERE module_ident = 1')
        old_files = cursor.fetchall()

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm42955', '209deb1f-1a46-4369-9e0d-18674cf58a3e', '2.0',
        'Preface to College Physics', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, 11, '', '', '', NULL, NULL,
        'en', '{}', '{}', '{}', NULL, NULL, NULL) RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]

        # Test that the latest row in modules is a collection with updated
        # version
        cursor.execute('SELECT * FROM modules m ORDER BY module_ident DESC')
        results = cursor.fetchone()
        new_collection_id = results[0]
        self.assertEqual(results[1], 'Collection')
        self.assertEqual(results[4], '1.8')
        self.assertEqual(results[5], 'College Physics')

        cursor.execute('SELECT nodeid FROM trees '
                'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        new_nodeid = cursor.fetchone()[0]

        sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr WHERE tr.nodeid = %(nodeid)s
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON c.parent_id = t.node
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t'''

        cursor.execute(sql, {'nodeid': old_nodeid})
        old_tree = cursor.fetchall()

        cursor.execute(sql, {'nodeid': new_nodeid})
        new_tree = cursor.fetchall()

        # Test that the new collection tree is identical to the old collection
        # tree except for the new document ids
        self.assertEqual(len(old_tree), len(new_tree))

        # make sure all the node ids are different from the old ones
        old_nodeids = [i[0] for i in old_tree]
        new_nodeids = [i[0] for i in new_tree]
        all_nodeids = old_nodeids + new_nodeids
        self.assertEqual(len(set(all_nodeids)), len(all_nodeids))

        new_document_ids = {
                # old module_ident: new module_ident
                1: new_collection_id,
                2: new_module_ident,
                }
        for i, old_node in enumerate(old_tree):
            self.assertEqual(new_document_ids.get(old_node[2], old_node[2]),
                    new_tree[i][2]) # documentid
            self.assertEqual(old_node[3], new_tree[i][3]) # title
            self.assertEqual(old_node[4], new_tree[i][4]) # child order
            self.assertEqual(old_node[5], new_tree[i][5]) # latest

    @db_connect
    def test_module_files(self, cursor):
        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm42119', 'f3c9ab70-a916-4d8c-9256-42953287b4e9', '2.0',
        'New Version', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, 11, '', '', '', NULL, NULL,
        'en', '{}', '{}', '{}', NULL, NULL, NULL) RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, m.mimetype
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, mimetype in cursor.fetchall():
            cursor.execute('''INSERT INTO files (file) VALUES (%s)
            RETURNING fileid''', (data,))
            fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            VALUES (%s, %s, %s, %s)''', (new_module_ident, fileid, filename,
                mimetype))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''
        INSERT INTO files (file)
            SELECT f.file
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml'
        RETURNING fileid
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            SELECT %s, %s, m.filename, m.mimetype
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
            (new_module_ident, fileid,))

        # Get the index.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.html' ''',
        (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we generated exactly one index.html for new_module_ident
        self.assertEqual(len(index_htmls), 1)
        # Test that the index.html contains html
        html = index_htmls[0][0][:]
        self.assert_('<html' in html)
