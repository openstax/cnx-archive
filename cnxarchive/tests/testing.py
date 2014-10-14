# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import functools

import psycopg2

from .. import config
from ..utils import parse_app_settings
from ..config import TEST_DATA_DIRECTORY as DATA_DIRECTORY
from ..config import TEST_DATA_SQL_FILE as DATA_SQL_FILE


__all__ = (
    'DATA_DIRECTORY', 'DATA_SQL_FILE',
    'db_connect', 'db_connection_factory',
    'integration_test_settings',
    'data_fixture', 'schema_fixture',
    )


here = os.path.abspath(os.path.dirname(__file__))
config_uri = None


def integration_test_settings():
    """Integration settings initializer"""
    global config_uri
    if config_uri is None:
        config_uri = os.environ.get('TESTING_CONFIG', None)
        if config_uri is None:
            config_uri = os.path.join(here, 'testing.ini')
    settings = parse_app_settings(config_uri)
    return settings


def db_connection_factory(connection_string=None):
    if connection_string is None:
        settings = integration_test_settings()
        connection_string = settings[config.CONNECTION_STRING]

    def db_connect():
        return psycopg2.connect(connection_string)

    return db_connect


def db_connect(method):
    """Decorator for methods that need to use the database

    Example::

    @db_connect
    def setUp(self, cursor):
        some_sql = "SELECT TRUE"
        cursor.execute(some_sql)
        # some other code

    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        connect = db_connection_factory()
        with connect() as db_connection:
            with db_connection.cursor() as cursor:
                return method(self, cursor, *args, **kwargs)
    return wrapped


class SchemaFixture(object):
    """A testing fixture for a live (same as production) SQL database.
    This will set up the database once for a test case. After each test
    case has completed, the database will be cleaned (all tables dropped).

    On a personal note, this seems archaic... Why can't I rollback to a
    transaction?
    """
    is_set_up = False

    def __init__(self):
        # Configure the database connection.
        self._settings = integration_test_settings()
        self.start_db_connection = db_connection_factory()
        # Drop all existing tables from the database.
        self._drop_all()

    @db_connect
    def _drop_all(self, cursor):
        """Drop all tables in the database."""
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        self.is_set_up = False

    def setUp(self):
        if self.is_set_up:
            # Failed to clean up after last use.
            self.tearDown()
        # Initialize the database schema.
        from ..database import initdb
        initdb(self._settings)
        self.is_set_up = True

    def tearDown(self):
        # Drop all tables.
        self._drop_all()


class DataFixture(SchemaFixture):
    """A testing fixture for a live (same as production) SQL database.
    This will set up the database and populate it with test data.
    After each test case has completed,
    the database will be cleaned (all tables dropped).
    """
    is_accounts_set_up = False

    @db_connect
    def setUp(self, cursor):
        super(DataFixture, self).setUp()
        # Load the database with example legacy data.
        with open(DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

    @property  # Returns a callable connection
    def db_connect_to_accounts(self):
        """Creates a connection to the OpenStax Accounts database."""
        settings = integration_test_settings()
        connection_string = settings[config.ACCOUNTS_CONNECTION_STRING]
        return db_connection_factory(connection_string)

    def setUpAccountsDb(self):
        """Initializes the OpenStax Accounts database. This is a NOOP
        if the database has already been setup. This database is read-only,
        so we do not tear it down. Instead we tear it down on first setup.
        """
        if self.is_accounts_set_up:
            return  # NOOP

        settings = integration_test_settings()
        connection_string = settings[config.ACCOUNTS_CONNECTION_STRING]
        schema_filepath = os.path.join(DATA_DIRECTORY,
                                       'osc-accounts.schema.sql')
        data_filepath = os.path.join(DATA_DIRECTORY,
                                     'osc-accounts.data.sql')

        with self.db_connect_to_accounts() as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("CREATE SCHEMA public")
                self.is_accounts_set_up = True
                # Initial the schema.
                with open(schema_filepath, 'r') as fb:
                    cursor.execute(fb.read())
                # Load the data.
                with open(data_filepath, 'r') as fb:
                    cursor.execute(fb.read())

    def tearDownAccountsDb(self):
        """Remove the accounts database. This needs to be manually called
        in a tests. For example, ``self.addCleanup(self.tearDownAccoutnsDb)``.
        """
        with self.db_connect_to_accounts() as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA PUBLIC cascade")
                cursor.execute("CREATE SCHEMA public")
        self.is_accounts_set_up = False


schema_fixture = SchemaFixture()
data_fixture = DataFixture()


# Set the timezone for the postgresql client so that we get the times in the
# right timezone (America/Whitehorse is -07 in summer and -08 in winter)
os.environ['PGTZ'] = 'America/Whitehorse'
os.environ['TZ'] = 'America/Whitehorse'
