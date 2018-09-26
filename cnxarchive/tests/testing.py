# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import functools
import os
import re
import sys
import unittest
import warnings
from datetime import datetime
from uuid import uuid4

import memcache
import pytz
import psycopg2
import psycopg2.extras
from psycopg2.extras import DictCursor
from pyramid.paster import get_appsettings

from .. import config
from ..config import TEST_DATA_DIRECTORY as DATA_DIRECTORY
from ..config import TEST_DATA_SQL_FILE as DATA_SQL_FILE


here = os.path.abspath(os.path.dirname(__file__))


def config_uri():
    """Return the file path of the testing config uri"""
    config_uri = os.environ.get('TESTING_CONFIG', None)
    if config_uri is None:
        config_uri = os.path.join(here, 'testing.ini')
    return config_uri


def mocked_fromtimestamp(timestamp):
    """Always return 2015-03-04 10:03:29-08:00"""
    return datetime.fromtimestamp(1425492209, tz=pytz.timezone('America/Whitehorse'))


def integration_test_settings():
    """Integration settings initializer"""
    settings = get_appsettings(config_uri(), name='main')
    return settings


def db_connection_factory(connection_string=None):
    if connection_string is None:
        settings = integration_test_settings()
        connection_string = settings[config.CONNECTION_STRING]

    def db_connect():
        return psycopg2.connect(connection_string, cursor_factory=DictCursor)

    return db_connect


def db_is_local(connection_string=None):
    if connection_string is None:
        settings = integration_test_settings()
        connection_string = settings[config.CONNECTION_STRING]

    parts = dict([i.split('=', 1) for i in connection_string.split()])
    return parts.get('host', 'localhost') == 'localhost'


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
                psycopg2.extras.register_default_json()
                return method(self, cursor, *args, **kwargs)
    return wrapped


class PlPy(object):
    """Class to wrap access to DB in plpy style api"""

    def __init__(self, cursor):
        """Set up the cursor and plan store"""
        self._cursor = cursor
        self._plans = {}

    def execute(self, query, args=None, rows=None):
        """Execute a query or plan, with interpolated args"""

        if query in self._plans:
            args_fmt = self._plans[query]
            self._cursor.execute('EXECUTE "{}"({})'.format(query, args_fmt), args)
        else:
            self._cursor.execute(query, args)

        if self._cursor.description is not None:
            if rows is None:
                res = self._cursor.fetchall()
            else:
                res = self._cursor.fetchmany(rows)
        else:
            res = None
        return res

    def prepare(self, query, args=None):
        """"Prepare a plan, with optional placeholders for EXECUTE"""

        plan = str(uuid4())
        if args:
            argstr = str(args).replace("'", '')
            if len(args) < 2:
                argstr = argstr.replace(',', '')
            self._cursor.execute('PREPARE "{}"{} AS {}'.format(plan, argstr, query))
        else:
            self._cursor.execute('PREPARE "{}" AS {}'.format(plan, query))

        self._plans[plan] = ', '.join(('%s',) * len(args))
        return plan


def plpy_connect(method):
    """Decorator for plpythonu trigger methods that need to use the database

    Example::

    @plpy_connect
    def setUp(self, plpy):
        some_sql = "SELECT TRUE"
        plpy.execute(some_sql)
        # some other code

    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        connect = db_connection_factory()
        with connect() as db_connection:
            with db_connection.cursor(
                    cursor_factory=psycopg2.extras.DictCursor) as cursor:
                plpy = PlPy(cursor)
                psycopg2.extras.register_default_json(globally=False, loads=lambda x: x)
                return method(self, plpy, *args, **kwargs)
    return wrapped


def is_venv():
    """Returns a boolean telling whether the application is running
    within a virtualenv (aka venv).

    """
    return hasattr(sys, 'real_prefix')


if not is_venv:
    # BBB (22-Apr-2016) https://github.com/pypa/virtualenv/issues/355
    from site import getsitepackages
else:
    # Copy of `site.getsitepackages` from the standard library.
    PREFIXES = [sys.prefix, sys.exec_prefix]

    def getsitepackages(prefixes=None):
        """Returns a list containing all global site-packages directories.
        For each directory present in ``prefixes`` (or the global ``PREFIXES``),
        this function will find its `site-packages` subdirectory depending on the
        system environment, and will return a list of full paths.
        """
        sitepackages = []
        seen = set()

        if prefixes is None:
            prefixes = PREFIXES

        for prefix in prefixes:
            if not prefix or prefix in seen:
                continue
            seen.add(prefix)

            if os.sep == '/':
                sitepackages.append(os.path.join(prefix, "lib",  # noqa
                                            "python%d.%d" % sys.version_info[:2],
                                            "site-packages"))
            else:
                sitepackages.append(prefix)
                sitepackages.append(os.path.join(prefix, "lib", "site-packages"))
            if sys.platform == "darwin":
                # for framework builds *only* we add the standard Apple
                # locations.
                from sysconfig import get_config_var
                framework = get_config_var("PYTHONFRAMEWORK")
                if framework:
                    sitepackages.append(  # noqa
                            os.path.join("/Library", framework,
                                '%d.%d' % sys.version_info[:2], "site-packages"))
        return sitepackages


def is_memcache_enabled():
    settings = integration_test_settings()
    memcache_servers = settings['memcache-servers'].split()
    mc = memcache.Client(memcache_servers, debug=0)
    is_enabled = bool(mc.get_stats())
    if not is_enabled:
        warnings.warn("memcached is not running, some tests will be skipped")
    return is_enabled


IS_MEMCACHE_ENABLED = is_memcache_enabled()


def _dsn_to_args(dsn):
    """Translates a libpq DSN to dict
    to be used with ``sqlalchemy.engine.url.URL``.
    """
    args = {'query': {}}
    import inspect
    from sqlalchemy.engine.url import URL
    url_args = inspect.getargspec(URL.__init__).args
    for item in dsn.split():
        name, value = item.split('=')
        if name == 'user':
            name = 'username'
        elif name == 'dbname':
            name = 'database'
        if name in url_args:
            args[name] = value
        else:
            args['query'][name] = value
    return args


def libpq_dsn_to_url(dsn):
    """Translate a libpq DSN to URL"""
    from sqlalchemy.engine.url import URL
    args = _dsn_to_args(dsn)
    url = URL('postgresql', **args)
    return str(url)


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
        from cnxdb.init import init_db
        from sqlalchemy import create_engine
        dsn = self._settings[config.CONNECTION_STRING]
        engine = create_engine(libpq_dsn_to_url(dsn))
        init_db(engine, True)
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


class FakePlpy(object):
    @staticmethod
    def prepare(stmt, param_types):
        return FakePlpyPlan(stmt)

    @staticmethod
    def execute(plan, args, rows=None):
        return plan.execute(args, rows=rows)


fake_plpy = FakePlpy()


class FakePlpyPlan(object):
    def __init__(self, stmt):
        self.stmt = re.sub(
            '\$([0-9]+)', lambda m: '%(param_{})s'.format(m.group(1)), stmt)

    def execute(self, args, rows=None):
        connect = db_connection_factory()
        with connect() as db_conn:
            with db_conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                params = {}
                for i, value in enumerate(args):
                    params['param_{}'.format(i + 1)] = value
                cursor.execute(self.stmt, params)
                try:
                    results = cursor.fetchall()
                    if rows is not None:
                        results = results[:rows]
                    return results
                except psycopg2.ProgrammingError as e:
                    if e.message != 'no results to fetch':
                        raise


class FunctionalTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = settings = integration_test_settings()
        # only run once for all the tests

        from .. import main
        app = main({}, **settings)

        from webtest import TestApp
        cls.testapp = TestApp(app)


__all__ = (
    'config_uri',
    'DATA_DIRECTORY',
    'data_fixture',
    'db_connect',
    'db_connection_factory',
    'fake_plpy',
    'integration_test_settings',
    'IS_MEMCACHE_ENABLED',
    'is_memcache_enabled',
    'is_venv',
    'mocked_fromtimestamp',
    'schema_fixture',
    'FunctionalTestCase',
    )
