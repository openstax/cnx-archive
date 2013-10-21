# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os

import psycopg2
from paste.deploy import appconfig

from ..database import CONNECTION_SETTINGS_KEY


__all__ = (
    'TESTING_CONFIG', 'TEST_DATA_DIRECTORY',
    'TESTING_DATA_SQL_FILE', 'TESTING_CNXUSER_DATA_SQL_FILE',
    'get_app_settings', 'db_connect',
    'postgresql_fixture',
    )


# Set the timezone for the postgresql client so that we get the times in the
# right timezone (America/Whitehorse is -07 in summer and -08 in winter)
os.environ['PGTZ'] = 'America/Whitehorse'

here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(here, 'data')
TESTING_DATA_SQL_FILE = os.path.join(TEST_DATA_DIRECTORY, 'data.sql')
TESTING_CNXUSER_DATA_SQL_FILE = os.path.join(TEST_DATA_DIRECTORY, 'cnx-user.data.sql')
try:
    TESTING_CONFIG = os.environ['TESTING_CONFIG']
except KeyError as exc:
    print("*** Missing 'TESTING_CONFIG' environment variable ***")
    raise exc


def get_app_settings(config_path):
    """Shortcut to the application settings. This does not load logging."""
    # This assumes the application is section is named 'main'.
    config_path = os.path.abspath(config_path)
    return appconfig("config:{}".format(config_path), name='main')


def db_connect(method):
    """Decorator for methods that need to use the database

    Example:
    @db_connection
    def setUp(self, cursor):
        cursor.execute(some_sql)
        # some other code
    """
    def wrapped(self, *args, **kwargs):
        from ..utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
            with db_connection.cursor() as cursor:
                return method(self, cursor, *args, **kwargs)
            db_connection.commit()
    return wrapped


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
        self._settings = get_app_settings(TESTING_CONFIG)
        self._connection_string = self._settings['db-connection-string']
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

postgresql_fixture = PostgresqlFixture()
