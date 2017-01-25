# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import psycopg2

from .. import testing


class InitializeDBTestCase(unittest.TestCase):
    fixture = testing.schema_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    def tearDown(self):
        self.fixture.tearDown()

    @property
    def target(self):
        from cnxarchive.scripts.initializedb import main
        return main

    @testing.db_connect
    def test_initialized(self, cursor):
        # Call the command line script.
        args = [testing.config_uri()]
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure the document_controls table has been setup.
        cursor.execute("SELECT count(*) FROM document_controls")
        record_count = cursor.fetchone()[0]
        self.assertEqual(record_count, 0)

    @testing.db_connect
    def test_initialized_with_example_data(self, cursor):
        args = [testing.config_uri(), '--with-example-data']
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure the the example data is in the database.
        cursor.execute("SELECT count(*) FROM document_controls")
        record_count = cursor.fetchone()[0]
        # Check for greater than or equal to one rather than equality
        # in case there are additions made to the example data.
        self.assertTrue(record_count >= 1)

    @mock.patch('sys.stderr')
    def test_error_on_already_initialized(self, mocked_stderr):
        # Load the schema to trigger an error.
        self.fixture.setUp()

        args = [testing.config_uri()]
        return_code = self.target(args)
        self.assertNotEqual(return_code, 0)

        # Ensure a meaningfully message was sent to stderr.
        expected_message_line = 'Error:  Database is already initialized.'
        call_args_repr = repr(mocked_stderr.write.call_args_list)
        # Postgres > 9.4 includes the raise location
        self.assertIn(expected_message_line, call_args_repr)
