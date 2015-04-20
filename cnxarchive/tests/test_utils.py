# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import uuid
import unittest
from .. import config


class ParserTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import app_parser
        return app_parser(*args, **kwargs)

    def test_positional_arguments(self):
        parser = self.call_target()
        args = parser.parse_args(['testing.ini'])
        self.assertEqual(args.config_uri, 'testing.ini')
        self.assertFalse(args.with_example_data)
        self.assertIsNone(args.superuser)
        self.assertIsNone(args.superpassword)
        self.assertEqual(args.config_name, 'main')
        self.assertIsNone(args.user)
        self.assertIsNone(args.password)

    def test_optional_arguments(self):
        parser = self.call_target()
        args = parser.parse_args(['testing.ini',
                                  '--with-example-data',
                                  '--superuser', 'superuser',
                                  '--superpassword', 'superpassword',
                                  '--user', 'user',
                                  '--password', 'password',
                                  '--config-name', 'NEW_NAME'])
        self.assertEqual(args.config_uri, 'testing.ini')
        self.assertTrue(args.with_example_data)
        self.assertEqual(args.superuser, 'superuser')
        self.assertEqual(args.superpassword, 'superpassword')
        self.assertEqual(args.config_name, 'NEW_NAME')
        self.assertEqual(args.user, 'user')
        self.assertEqual(args.password, 'password')

    def test_help(self):
        import subprocess
        parser = self.call_target(
            description='Commandline script '
                        'used to initialize the SQL database.')
        expected_help_message = parser.format_help()
        actual_help_message = subprocess.check_output(
            ["cnx-archive-initdb", "--help"])
        expected_help_message = expected_help_message.split()
        actual_help_message = actual_help_message.split()
        self.assertEqual(expected_help_message, actual_help_message)


class SettingsTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import app_settings
        from ..utils import app_parser
        parser = app_parser()
        arguments = parser.parse_args(*args, **kwargs)
        return app_settings(arguments)

    def test_default_config(self):
        from testing import integration_test_settings
        import os
        expected = integration_test_settings()
        here = os.path.abspath(os.path.dirname(__file__))
        config_uri = os.path.join(here, 'testing.ini')
        settings = self.call_target([config_uri])
        self.assertFalse(settings['with_example_data'])
        self.assertEqual(settings['user'], 'cnxarchive')
        self.assertEqual(settings['password'], 'cnxarchive')
        self.assertIsNone(settings[config.SUPER_CONN_STRING])
        self.assertEqual(
            settings[config.CONNECTION_STRING],
            'dbname=cnxarchive-testing '
            'user=cnxarchive '
            'password=cnxarchive '
            'host=localhost '
            'port=5432')

    def test_custom_settings(self):
        settings = self.call_target(['cnxarchive/tests/testing.ini',
                                     '--with-example-data',
                                     '--superuser', 'superuser',
                                     '--superpassword', 'superpassword',
                                     '--user', 'user',
                                     '--password', 'password'])
        self.assertTrue(settings['with_example_data'])
        self.assertEqual(settings['superuser'], 'superuser')
        self.assertEqual(settings['superpassword'], 'superpassword')
        self.assertEqual(settings['config_name'], 'main')
        self.assertEqual(settings['user'], 'user')
        self.assertEqual(settings['password'], 'password')
        self.assertEqual(
            settings[config.SUPER_CONN_STRING],
            'dbname=cnxarchive-testing '
            'user=superuser '
            'password=superpassword '
            'host=localhost '
            'port=5432')


class SplitIdentTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import split_ident_hash
        return split_ident_hash(*args, **kwargs)

    def test_empty_value(self):
        # Case of supplying the utility function with an empty indent-hash.
        ident_hash = ''

        with self.assertRaises(ValueError):
            self.call_target(ident_hash)

    def test_complete_data(self):
        # Simple case of supplying the correct information and checking
        # for the correct results.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '1.12',
            )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        id, version = self.call_target(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_uuid_only(self):
        # Case where the UUID has been the only value supplied in the
        # ident-hash.
        # This is mostly testing that the version value returns None.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '',
            )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        id, version = self.call_target(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, None)

    def test_invalid_id(self):
        # Case for testing for an invalid identifier.
        ident_hash = "not-a-valid-id@"

        from ..utils import IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            self.call_target(ident_hash)

    def test_invalid_syntax(self):
        # Case for testing the ident-hash's syntax guards.
        ident_hash = "85e57f7902b347d28eedc1bbb1e1d5c2@1.2@select*frommodules"

        from ..utils import IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            self.call_target(ident_hash)

    def test_w_split_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            ('1', '12',),
            )
        ident_hash = "{}@{}".format(expected_id, '.'.join(expected_version))

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_w_split_version_on_major_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            ('1', None,),
            )
        ident_hash = "{}@{}".format(expected_id, expected_version[0])

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_w_split_version_no_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            (None, None,)
            )
        ident_hash = expected_id

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)


class JoinIdentTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import join_ident_hash
        return join_ident_hash(*args, **kwargs)

    def test(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('2', '4',)
        expected = "{}@{}".format(id, '.'.join(version))
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_UUID(self):
        id = uuid.uuid4()
        version = None
        expected = str(id)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_null_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = None
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_null_str_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ''
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_str_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = '2'
        expected = "{}@{}".format(id, version)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_major_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('2', None,)
        expected = "{}@{}".format(id, version[0])
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)


    def test_w_double_null_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = (None, None,)
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_invalid_version_sequence(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('1',)
        with self.assertRaises(AssertionError):
            self.call_target(id, version)

    def test_w_integer_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = (1, 2,)
        expected = '{}@1.2'.format(id)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)


class SlugifyTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import slugify
        return slugify(*args, **kwargs)

    def test_ascii(self):
        self.assertEqual(self.call_target('How to Work for Yourself: 100 Ways'),
                'how-to-work-for-yourself-100-ways')

    def test_hyphen(self):
        self.assertEqual(self.call_target('Any Red-Blooded Girl'),
                         'any-red-blooded-girl')

    def test_underscore(self):
        self.assertEqual(self.call_target('Underscores _hello_'),
                         'underscores-_hello_')

    def test_unicode(self):
        self.assertEqual(self.call_target('Radioactive (Die Verstoßenen)'),
                         u'radioactive-die-verstoßenen')

        self.assertEqual(self.call_target(u'40文字でわかる！'
                                          u'　知っておきたいビジネス理論'),
                         u'40文字でわかる-知っておきたいビジネス理論')

class EscapeTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import escape
        return escape(*args, **kwargs)

    def test_ascii(self):
        self.assertEqual(self.call_target('How to Work for Yourself: 100 Ways'),
                'How to Work for Yourself: 100 Ways')

    def test_greater(self):
        self.assertEqual(self.call_target('this > that'),
                         'this &gt; that')

    def test_less(self):
        self.assertEqual(self.call_target('this < that'),
                         'this &lt; that')

    def test_amp(self):
        self.assertEqual(self.call_target('this & that'),
                         'this &amp; that')



class Utf8TestCase(unittest.TestCase):
    def call_target(self, *args, **kwargs):
        from ..utils import utf8
        return utf8(*args, **kwargs)

    def test_str(self):
        self.assertEqual(self.call_target('inførmation'), u'inførmation')

    def test_unicode(self):
        self.assertEqual(self.call_target(u'inførmation'), u'inførmation')

    def test_not_str(self):
        self.assertEqual(self.call_target(1), 1)

    def test_list(self):
        self.assertEqual([u'infør', u'mation'],
                         self.call_target(['infør', 'mation']))

    def test_tuple(self):
        self.assertEqual((u'infør', u'mation',),
                         self.call_target(('infør', 'mation',)))

    def test_dict(self):
        self.assertEqual({u'inførmation': u'inførm'},
                         self.call_target({'inførmation': 'inførm'}))
