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


class MetadataGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_metadata
        return get_metadata

    def assert_contains(self, l1, l2):
        """Check that ``l1`` contains ``l2``"""
        not_in = [i for i in l2 if i not in l1]
        if not_in:
            self.fail("Could not find {} in:\n {}"
                      .format(not_in, l1))

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd'
        from cnxarchive.scripts.export_epub import NotFound
        try:
            doc = self.target(ident_hash)
        except NotFound:
            pass
        else:
            self.fail("this should not have found an entry")

    def test_get(self):
        id, version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = '{}@{}'.format(id, version)
        metadata = self.target(ident_hash)

        metadata_keys = [
            'id', 'version',
            'title', 'language', 'created', 'revised',
            'license_url', 'license_text',
            'summary', 'subjects', 'keywords',
            'cnx-archive-uri',
            # People keys
            'authors', 'editors', 'illustrators', 'publishers',
            'copyright_holders',
            # Print style
            'print_style',
            # Derivation keys
            'derived_from_uri', 'derived_from_title',
            ]
        required_keys = metadata_keys[:16]
        self.assert_contains(metadata, required_keys)

        self.assertEqual(metadata['id'], id)
        self.assertEqual(metadata['version'], version)

        self.assertEqual(metadata['title'], u"Atomic Masses")
        self.assertEqual(metadata['language'], u'en')
        self.assertEqual(metadata['created'], u'2013-07-31T19:07:25Z')
        self.assertEqual(metadata['revised'], u'2013-07-31T19:07:25Z')
        self.assertEqual(metadata['license_url'],
                         u'http://creativecommons.org/licenses/by/4.0/')
        self.assertEqual(metadata['license_text'],
                         u'Creative Commons Attribution License')
        self.assertEqual(metadata['summary'], None)  # FIXME Bad data
        self.assertEqual(metadata['subjects'], [u'Science and Technology'])
        self.assertEqual(metadata['keywords'], [])
        self.assertEqual(metadata['cnx-archive-uri'],
                         u'f6024d8a-1868-44c7-ab65-45419ef54881@3')

        roles = [
            {u'firstname': u'OpenStax College',
             u'name': u'OpenStax College',
             u'id': u'OpenStaxCollege',
             u'type': 'cnx-id',
             u'suffix': None,
             u'surname': None,
             u'title': None},
            {u'firstname': u'Rice',
             u'name': u'Rice University',
             u'id': u'OSCRiceUniversity',
             u'type': 'cnx-id',
             u'suffix': None,
             u'surname': u'University',
             u'title': None},
            {u'firstname': u'OpenStax College',
             u'name': u'OpenStax College',
             u'id': u'OpenStaxCollege',
             u'type': 'cnx-id',
             u'suffix': None,
             u'surname': None,
             u'title': None},
            {u'firstname': u'College',
             u'name': u'OSC Physics Maintainer',
             u'id': u'cnxcap',
             u'type': 'cnx-id',
             u'suffix': None,
             u'surname': u'Physics',
             u'title': None},
            ]
        self.assertEqual(metadata['authors'], [roles[0]])
        self.assertEqual(metadata['editors'], [])
        self.assertEqual(metadata['illustrators'], [])
        self.assertEqual(metadata['translators'], [])
        self.assertEqual(metadata['publishers'], roles[2:])
        self.assertEqual(metadata['copyright_holders'], [roles[1]])

        self.assertEqual(metadata['print_style'], None)
        self.assertEqual(metadata['derived_from_uri'], None)
        self.assertEqual(metadata['derived_from_title'], None)


class ContentGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_content
        return get_content

    def test_get(self):
        ident_hash = 'f6024d8a-1868-44c7-ab65-45419ef54881@3'
        content = self.target(ident_hash)
        self.assertIn('<span class="title">Atomic Masses</span>', content)

    def test_not_found(self):
        # Use a collection's id to fake this.
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'

        from cnxarchive.scripts.export_epub import ContentNotFound
        try:
            self.target(ident_hash)
        except ContentNotFound:
            pass
        else:
            self.fail("should not have found content")
