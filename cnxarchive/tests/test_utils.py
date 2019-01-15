# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import uuid
import unittest


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
        self.assertEqual((u'infør', u'mation', ),
                         self.call_target(('infør', 'mation', )))

    def test_dict(self):
        self.assertEqual({u'inførmation': u'inførm'},
                         self.call_target({'inførmation': 'inførm'}))


class SafeStatTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import safe_stat
        return safe_stat(*args, **kwargs)

    def test_success(self):
        self.assertTrue(self.call_target('/tmp', 1))

    def test_timeout(self):
        self.assertFalse(self.call_target('/tmp', 1, cmd=['/bin/sleep', '10']))
