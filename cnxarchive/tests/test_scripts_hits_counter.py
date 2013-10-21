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


TEST_VARNISH_LOG = os.path.join(TEST_DATA_DIRECTORY, 'varnish.log')

SQL_FOR_HIT_DOCUMENTS = """
ALTER TABLE modules DISABLE TRIGGER ALL;
INSERT INTO abstracts VALUES (1, '');
INSERT INTO modules VALUES (
  1, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.1', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  2, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.2', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 2, NULL);
INSERT INTO modules VALUES (
  3, 'Module', 'm2', 'f122af91-5f4f-4736-a502-67bd0a1628aa',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  4, 'Module', 'm3', 'c8ee8dc5-bb73-47c8-b10f-3f37123cf607',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
ALTER TABLE modules ENABLE TRIGGER ALL;
"""


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
