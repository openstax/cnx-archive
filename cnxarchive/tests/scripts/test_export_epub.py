# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest

import cnxepub
from pyramid import testing as pyramid_testing

from .. import testing


class BaseTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()
        # This is a read-only testcase, only setup once
        cls.fixture.setUp()

    def setUp(self):
        self.config = pyramid_testing.setUp(settings=self.settings)

    def tearDown(self):
        pyramid_testing.tearDown()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDown()


class IdAndVersionGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_id_n_version
        return get_id_n_version

    def test_get(self):
        _id, _version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = '{}@{}'.format(_id, _version)

        id, version = self.target(ident_hash)
        self.assertEqual(id, _id)
        self.assertEqual(version, _version)

    def test_get_without_version(self):
        _id, _version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = _id

        id, version = self.target(ident_hash)
        self.assertEqual(id, _id)
        self.assertEqual(version, _version)

    def test_raises_syntax_error(self):
        _id, _version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = '{}@{}'.format(_id, '')

        from cnxarchive.utils import IdentHashSyntaxError
        try:
            id, version = self.target(ident_hash)
        except IdentHashSyntaxError:
            pass
        else:
            self.fail("should have raised a syntax error")

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd'

        from cnxarchive.scripts.export_epub import NotFound
        try:
            id, version = self.target(ident_hash)
        except NotFound:
            pass
        else:
            self.fail("should have not found any content")

    def test_not_found_with_version(self):
        _id, _version = ('31b37e2b-9abf-4923-b2fa-de004a3cb6cd', '3')
        ident_hash = '{}@{}'.format(_id, _version)

        from cnxarchive.scripts.export_epub import NotFound
        try:
            id, version = self.target(ident_hash)
        except NotFound:
            pass
        else:
            self.fail("should have not found any content")
