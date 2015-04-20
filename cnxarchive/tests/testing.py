# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import pytz
import functools
from datetime import datetime

import psycopg2


from .. import config
from ..utils import app_settings, app_parser
from ..config import TEST_DATA_DIRECTORY as DATA_DIRECTORY
from ..config import TEST_DATA_SQL_FILE as DATA_SQL_FILE
import unittest


__all__ = (
    'DATA_DIRECTORY', 'DATA_SQL_FILE',
    'db_connect', 'db_connection_factory',
    'integration_test_settings',
    'data_fixture', 'schema_fixture',
    )


here = os.path.abspath(os.path.dirname(__file__))
config_uri = None

def mocked_fromtimestamp(timestamp):
    """Always return 2015-03-04 10:03:29-08:00"""
    return datetime.fromtimestamp(1425492209, tz=pytz.timezone('America/Whitehorse'))

def integration_test_settings():
    """Integration settings initializer"""
    global config_uri
    if config_uri is None:
        config_uri = os.environ.get('TESTING_CONFIG', None)
        if config_uri is None:
            config_uri = os.path.join(here, 'testing.ini')
    parser = app_parser()
    args = parser.parse_args([config_uri])
    settings = app_settings(args)
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
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
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

    @db_connect
    def setUp(self, cursor):
        super(DataFixture, self).setUp()
        # Load the database with example legacy data.
        with open(DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())


schema_fixture = SchemaFixture()
data_fixture = DataFixture()


# Set the timezone for the postgresql client so that we get the times in the
# right timezone (America/Whitehorse is -07 in summer and -08 in winter)
os.environ['PGTZ'] = 'America/Whitehorse'
os.environ['TZ'] = 'America/Whitehorse'


class SingleInitDBTest(unittest.TestCase):

    """ A custom test class that allows for the default settings
        of the testing configuration to be changed for unit
        tests.
    """
    ##########################################################
    # FIXME: setUpClass and tearDownClass make redudant      #
    # DROP ... IF EXISTS calls to run the test without       #
    # errors.  Tests should be set up to avoid this          #
    ##########################################################
    @classmethod
    def setUpClass(cls):
        from ..database import initdb
        argv = [
            'cnxarchive/tests/testing.ini',
            '--user',
            'rich',
            '--password',
            'rich',
            '--superuser',
            'cnxarchive',
            '--superpassword',
            'cnxarchive']

        config_uri = os.path.join(here, argv[0])
        parser = app_parser()
        args = parser.parse_args(argv)
        cls._settings = app_settings(args)

        cls._super_conn = psycopg2.connect(
            cls._settings[config.SUPER_CONN_STRING])
        with cls._super_conn as connection:
            with connection.cursor() as cursor:
                cursor.execute("DROP EXTENSION IF EXISTS plpythonu CASCADE")
                cursor.execute("DROP LANGUAGE IF EXISTS plpythonu CASCADE")
                cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
                cursor.execute("DROP USER IF EXISTS rich")
                cursor.execute("CREATE SCHEMA IF NOT EXISTS public ")
                cursor.execute(
                    "CREATE USER rich WITH NOSUPERUSER PASSWORD 'rich'")
        cls._super_conn.commit()
        cls._super_conn.autocommit = False

        initdb(cls._settings)
        cls._connection = psycopg2.connect(
            cls._settings[config.CONNECTION_STRING])
        cls._connection.commit()

        cls._connection.autocommit = False

    @classmethod
    def tearDownClass(cls):
        with cls._super_conn as connection:
            with connection.cursor() as cursor:
                cursor.execute("DROP EXTENSION IF EXISTS plpythonu CASCADE")
                cursor.execute("DROP LANGUAGE IF EXISTS plpythonu CASCADE")
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("DROP USER IF EXISTS rich")
                cursor.execute("CREATE SCHEMA public")
        cls._connection.close()
        cls._super_conn.close()

    def setUp(self):
        """ Commit changes to the connection before
            test is called so the db connection can
            be rolled back to the start of the test
            on completion.
        """
        with self._connection as connection:
            connection.commit()
        with self._super_conn as connection:
            connection.commit()

    def tearDown(self):
        """ Rollback the db to a state before a
            test was called.
        """
        with self._connection as connection:
            connection.rollback()
        with self._super_conn as connection:
            connection.rollback()

    def test_class_setup(self):
        """ Blank function to test class setUp and tearDown functions
        """
        pass
