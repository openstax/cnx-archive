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
from .. import testing
from ..test_database import SQL_FOR_HIT_DOCUMENTS


TEST_VARNISH_LOG = os.path.join(testing.DATA_DIRECTORY, 'varnish.log')


class HitsCounterTestCase(unittest.TestCase):
    fixture = testing.schema_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        # Input module stubs for module_ident relationship foreign keys.
        cursor.execute(SQL_FOR_HIT_DOCUMENTS)

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def override_recent_date(self, cursor):
        # Override the SQL function for acquiring the recent date,
        #   because otherwise the test will be a moving target in time.
        cursor.execute("CREATE OR REPLACE FUNCTION get_recency_date () "
                       "RETURNS TIMESTAMP AS $$ BEGIN "
                       # 'varnish.log' timestamps are between 18-20.
                       "  RETURN '2013-10-17'::timestamp with time zone; "
                       "END; $$ LANGUAGE plpgsql;")

    @testing.db_connect
    def test_insertion(self, cursor):
        # Call the command line script.
        args = ['--log-format', 'plain', testing.config_uri(),
                TEST_VARNISH_LOG]
        from cnxarchive.scripts.hits_counter import main
        return_code = main(args)
        self.assertEqual(return_code, 0)

        expectations = [[1, 3], [2, 1], [3, 4], [4, 1]]
        # Check for the insertion of data.
        cursor.execute("SELECT documentid, hits "
                       "  FROM document_hits;")
        hits = cursor.fetchall()
        hits = sorted(hits)
        self.assertEqual(hits, expectations)

    @testing.db_connect
    def test_updates_optimization_tables(self, cursor):
        self.override_recent_date()
        # Call the command line script.
        args = ['--log-format', 'plain', testing.config_uri(),
                TEST_VARNISH_LOG]
        from cnxarchive.scripts.hits_counter import main
        main(args)

        # Check the optimization tables for content.
        cursor.execute("SELECT count(*) from recent_hit_ranks;")
        recent_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) from overall_hit_ranks;")
        overall_count = cursor.fetchone()[0]
        self.assertTrue(recent_count > 0)
        self.assertTrue(overall_count > 0)
