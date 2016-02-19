# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

from .. import testing


class ParserTestCase(unittest.TestCase):

    @property
    def target(self):
        from cnxarchive.scripts._utils import create_parser
        return create_parser

    def test_positional_arguments(self):
        parser = self.target('moo')
        args = parser.parse_args([testing.config_uri()])
        self.assertEqual(args.config_uri, testing.config_uri())
        self.assertEqual(args.config_name, 'main')

    def test_optional_arguments(self):
        parser = self.target('oik')
        args = parser.parse_args([testing.config_uri(),
                                  '--config-name', 'NEW_NAME'])
        self.assertEqual(args.config_uri, testing.config_uri())
        self.assertEqual(args.config_name, 'NEW_NAME')

    def test_help(self):
        name = 'cluck'
        parser = self.target(
            name,
            description='Commandline script '
                        'used to initialize the SQL database.')
        help_ = parser.format_help()
        self.assertIn('cnx-archive-{}'.format(name), help_)
        self.assertIn('show this help message and exit', help_)


class SettingsTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from cnxarchive.scripts._utils import create_parser
        from cnxarchive.scripts._utils import get_app_settings_from_arguments
        parser = create_parser('settings-test', 'just a test')
        arguments = parser.parse_args(*args, **kwargs)
        return get_app_settings_from_arguments(arguments)

    def test_default_config(self):
        expected = testing.integration_test_settings()
        result = self.call_target([testing.config_uri()])
        self.assertEqual(expected, result)
