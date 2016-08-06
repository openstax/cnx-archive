# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import hashlib
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import psycopg2
from pyramid import testing as pyramid_testing

from .. import testing


class UpsertModuleFileTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

        # Insert files for testing against
        cursor.execute("INSERT INTO files (file, media_type) "
                       "VALUES (%s, %s), (%s, %s)"
                       "RETURNING fileid",
                       (psycopg2.Binary("abc"), 'text/plain',
                        psycopg2.Binary("xyz"), 'text/plain',))
        self.fileids = [r[0] for r in cursor.fetchall()]

        pyramid_testing.setUp(settings=self.settings)

    def tearDown(self):
        self.fixture.tearDown()
        pyramid_testing.tearDown()

    @property
    def target(self):
        from cnxarchive.scripts.inject_resource import upsert_module_file
        return upsert_module_file

    @testing.db_connect
    def test_insert(self, cursor):
        module_ident = 1
        filename = 'ruleset.css'

        self.target(module_ident, self.fileids[0], filename)

        # Check for the module_files entry
        cursor.execute("SELECT fileid "
                       "FROM module_files "
                       "WHERE module_ident = %s and filename = %s",
                       (module_ident, filename,))
        self.assertEqual(cursor.fetchone()[0], self.fileids[0])

    @testing.db_connect
    def test_upsert(self, cursor):
        module_ident = 1
        filename = 'ruleset.css'

        self.target(module_ident, self.fileids[0], filename)
        self.target(module_ident, self.fileids[1], filename)

        # Check for the module_files entry
        cursor.execute("SELECT fileid "
                       "FROM module_files "
                       "WHERE module_ident = %s and filename = %s",
                       (module_ident, filename,))
        self.assertEqual(cursor.fetchone()[0], self.fileids[1])


class InjectResourceTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @property
    def target(self):
        from cnxarchive.scripts.inject_resource import main
        return main

    collection_ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'
    module_ident_hash = 'c0a76659-c311-405f-9a99-15c71af39325@5'
    data_filename = "e3d625fe.png"
    media_type = 'image/png'

    @property
    def data_filepath(self):
        return os.path.join(testing.DATA_DIRECTORY, self.data_filename)

    @property
    def data_sha1(self):
        sha1 = getattr(self, '_data_sha1', None)
        if sha1 is None:
            with open(self.data_filepath, 'rb') as f:
                sha1 = hashlib.new('sha1', f.read()).hexdigest()
                self._data_sha1 = sha1
        return sha1

    @mock.patch('sys.stderr')
    @mock.patch('sys.stdout')
    def test_success_output_for_collection(self, stdout, stderr):
        # Call the command line script.
        args = (testing.config_uri(), self.collection_ident_hash,
                self.data_filepath,)
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure output to standard error and out contain expected output.
        expected_stderr_lines = [
            "  filename: {}".format(self.data_filename),
            "  media_type: {}".format(self.media_type),
            ]
        expected_stdout_lines = [
            "/resources/{}".format(self.data_sha1),
            ]
        for line in expected_stderr_lines:
            stderr.write.assert_any_call(line)
        for line in expected_stdout_lines:
            stdout.write.assert_any_call(line)

    @mock.patch('sys.stderr')
    @mock.patch('sys.stdout')
    def test_success_output_for_module(self, stdout, stderr):
        # Call the command line script.
        args = (testing.config_uri(), self.module_ident_hash,
                self.data_filepath,)
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure output to standard error and out contain expected output.
        expected_stderr_lines = [
            "  filename: {}".format(self.data_filename),
            "  media_type: {}".format(self.media_type),
            ]
        expected_stdout_lines = [
            "/resources/{}".format(self.data_sha1),
            ]
        for line in expected_stderr_lines:
            stderr.write.assert_any_call(line)
        for line in expected_stdout_lines:
            stdout.write.assert_any_call(line)

    @testing.db_connect
    def test_artifacts_of_injection(self, cursor):
        # Call the command line script.
        args = (testing.config_uri(), self.collection_ident_hash,
                self.data_filepath,)
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure the resource has been insert into the files table.
        cursor.execute("SELECT media_type FROM files WHERE sha1 = %s",
                       (self.data_sha1,))
        media_type = cursor.fetchone()[0]
        self.assertEqual(media_type, self.media_type)

        # Ensure the resource has been an entry in the module_files table.
        cursor.execute("SELECT true FROM module_files NATURAL JOIN files "
                       "WHERE sha1 = %s AND filename = %s",
                       (self.data_sha1, self.data_filename,))
        try:
            cursor.fetchone()[0]
        except (IndexError, TypeError):
            self.fail("did not find the file in the module_files table.")

    @testing.db_connect
    @mock.patch('sys.stderr')
    def test_media_type_override(self, cursor, stderr):
        # Call the command line script.
        media_type_override = 'image/tiff'
        args = (testing.config_uri(), self.collection_ident_hash,
                self.data_filepath,
                '--media-type', media_type_override,
                )
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure the resource has been insert into the files table.
        cursor.execute("SELECT media_type FROM files WHERE sha1 = %s",
                       (self.data_sha1,))
        media_type = cursor.fetchone()[0]
        self.assertEqual(media_type, media_type_override)

        expected_line = "  media_type: {}".format(media_type_override)
        stderr.write.assert_any_call(expected_line)

    @testing.db_connect
    @mock.patch('sys.stderr')
    def test_filename_override(self, cursor, stderr):
        # Call the command line script.
        filename_override = 'real-alternatives.png'
        args = (testing.config_uri(), self.collection_ident_hash,
                self.data_filepath,
                '--resource-filename', filename_override,
                )
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        # Ensure the resource has been insert into the files table.
        cursor.execute("SELECT true FROM module_files NATURAL JOIN files "
                       "WHERE sha1 = %s AND filename = %s",
                       (self.data_sha1, filename_override,))
        try:
            cursor.fetchone()[0]
        except (IndexError, TypeError):
            self.fail("did not find the file in the module_files table.")

        expected_line = "  filename: {}".format(filename_override)
        stderr.write.assert_any_call(expected_line)

    @testing.db_connect
    def test_nonexistent_content(self, cursor):
        """Raise an error and fail to enter the resource."""
        # Call the command line script.
        nonexistent_ident_hash = "d73d373a-12e2-4ed0-a716-5f77b1cb9029@23.12"
        args = (
            testing.config_uri(),
            nonexistent_ident_hash,
            self.data_filepath,
            )
        try:
            self.target(args)
        except RuntimeError:
            pass
        else:
            self.fail("should have errored, but did not.")

        # Ensure the resource has been insert into the files table.
        cursor.execute("SELECT true FROM files WHERE sha1 = %s",
                       (self.data_sha1,))
        try:
            cursor.fetchone()[0]
        except (IndexError, TypeError):
            pass
        else:
            self.fail("committed the file when it should not have")
