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
from . import *
from .test_database import SQL_FOR_HIT_DOCUMENTS


TEST_VARNISH_LOG = os.path.join(TEST_DATA_DIRECTORY, 'varnish.log')


class HitsCounterTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        from ..utils import parse_app_settings
        cls.settings = parse_app_settings(TESTING_CONFIG)
        from ..database import CONNECTION_SETTINGS_KEY
        cls.db_connection_string = cls.settings[CONNECTION_SETTINGS_KEY]

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        # Input module stubs for module_ident relationship foreign keys.
        cursor.execute(SQL_FOR_HIT_DOCUMENTS)

    def tearDown(self):
        self.fixture.tearDown()

    def test_insertion(self):
        # Call the command line script.
        args = ['--log-format', 'plain', TESTING_CONFIG, TEST_VARNISH_LOG]
        from ..scripts.hits_counter import main
        return_code = main(args)
        self.assertEqual(return_code, 0)

        expectations = [(1, 3), (2, 1), (3, 4), (4, 1)]
        # Check for the insertion of data.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT documentid, hits "
                               "  FROM document_hits;")
                hits = cursor.fetchall()
        hits = sorted(hits)
        self.assertEqual(hits, expectations)

    def test_updates_optimization_tables(self):
        # Call the command line script.
        args = ['--log-format', 'plain', TESTING_CONFIG, TEST_VARNISH_LOG]
        from ..scripts.hits_counter import main
        main(args)

        # Check the optimization tables for content.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT count(*) from recent_hit_ranks;")
                recent_count = cursor.fetchone()[0]
                cursor.execute("SELECT count(*) from overall_hit_ranks;")
                overall_count = cursor.fetchone()[0]
        self.assertTrue(recent_count > 0)
        self.assertTrue(overall_count > 0)
