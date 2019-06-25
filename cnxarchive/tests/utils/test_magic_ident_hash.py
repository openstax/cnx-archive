# -*- coding: utf-8 -*-
import unittest

from pyramid import testing as pyramid_testing

from .. import testing


class MagicallySplitIdentHashTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()
        cls.fixture.setUp()

    def setUp(self):
        config = pyramid_testing.setUp(settings=self.settings)

    @classmethod
    def tearDownClass(cls):
        pyramid_testing.tearDown()
        cls.fixture.tearDown()

    @property
    def target(self):
        from cnxarchive.utils.magic_ident_hash import magically_split_ident_hash
        return magically_split_ident_hash

    def test_error(self):
        from cnxcommon.ident_hash import IdentHashSyntaxError
        self.assertRaises(IdentHashSyntaxError, self.target, 'foo-bar-baz')

    def test_single(self):
        y = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        bih, pih = self.target(y)
        self.assertEqual(bih, None)
        self.assertEqual(pih, ('209deb1f-1a46-4369-9e0d-18674cf58a3e', '7',))

    def test_book_and_page(self):
        y = 'e79ffde3-7fb4-4af3-9ec8-df648b391597:209deb1f-1a46-4369-9e0d-18674cf58a3e'
        bih, pih = self.target(y)
        self.assertEqual(bih, ('e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1',))
        self.assertEqual(pih, ('209deb1f-1a46-4369-9e0d-18674cf58a3e', '7',))

    def test_short_ids(self):
        y = '55_943-0@7.1:IJ3rHxpG@7'
        bih, pih = self.target(y)
        self.assertEqual(bih, ('e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1',))
        self.assertEqual(pih, ('209deb1f-1a46-4369-9e0d-18674cf58a3e', '7',))

    def test_short_ids_wo_versions(self):
        y = '55_943-0:IJ3rHxpG'
        bih, pih = self.target(y)
        self.assertEqual(bih, ('e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1',))
        self.assertEqual(pih, ('209deb1f-1a46-4369-9e0d-18674cf58a3e', '7',))
