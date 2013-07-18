# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

import psycopg2
from paste.deploy import appconfig


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
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_something(self):
        pass
