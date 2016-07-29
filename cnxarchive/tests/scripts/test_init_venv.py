# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys
import unittest

import psycopg2

from .. import testing


class InitVenvTestCase(unittest.TestCase):
    fixture = testing.schema_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @property
    def target(self):
        from ...scripts.init_venv import main
        return main

    @testing.db_connect
    def test_success(self, cursor):
        # drop schema venv
        cursor.execute('DROP SCHEMA IF EXISTS venv CASCADE')
        cursor.connection.commit()

        self.target(argv=[testing.config_uri()])

        # test copied from pyimport

        target_name = 'cnxarchive.database'

        # Import the module from current directory
        import cnxarchive.database as target_source

        # Remove current directory from sys.path
        cwd = os.getcwd()
        sys_path = sys.path
        modified_path = [i for i in sys_path if i and i != cwd]
        sys.path = modified_path
        self.addCleanup(setattr, sys, 'path', sys_path)

        # Remove all cnxarchive modules from sys.modules
        sys_modules = sys.modules.copy()
        self.addCleanup(sys.modules.update, sys_modules)
        for module in sys.modules.keys():
            if module.startswith('cnxarchive'):
                del sys.modules[module]

        # Import the installed version
        import cnxarchive.database as target_installed

        # Depending on whether "setup.py develop" or "setup.py install" is
        # used, there are different expected directories and file paths.
        targets = [target_source, target_installed]
        expected_directories = [
            os.path.abspath(os.path.dirname(target.__file__))
            for target in targets]
        expected_file_paths = [
            target.__file__ for target in targets]

        # Check the results of calling pyimport on cnxarchive.
        cursor.execute("SELECT import, directory, file_path "
                       "FROM pyimport(%s)", (target_name,))
        import_, directory, file_path = cursor.fetchone()

        self.assertEqual(import_, target_name)
        self.assertIn(directory, expected_directories)
        self.assertIn(file_path, expected_file_paths)

    @testing.db_connect
    def test_rerun(self, cursor):
        # running init_venv multiple times shouldn't error
        self.target(argv=[testing.config_uri()])
        self.target(argv=[testing.config_uri()])
