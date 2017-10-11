# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import re
import tempfile
import unittest
import zipfile

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

    def assert_contains(self, l1, l2):
        """Check that ``l1`` contains ``l2``"""
        not_in = [i for i in l2 if i not in l1]
        if not_in:
            self.fail("Could not find {} in:\n {}"
                      .format(not_in, l1))


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
        with self.assertRaises(IdentHashSyntaxError) as e:
            id, version = self.target(ident_hash)

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd'

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            id, version = self.target(ident_hash)

    def test_not_found_with_version(self):
        _id, _version = ('31b37e2b-9abf-4923-b2fa-de004a3cb6cd', '3')
        ident_hash = '{}@{}'.format(_id, _version)

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            id, version = self.target(ident_hash)


class TypeGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_type
        return get_type

    def test_get(self):
        _id, _version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = '{}@{}'.format(_id, _version)

        type = self.target(ident_hash)
        self.assertEqual(type, 'Module')


class MetadataGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_metadata
        return get_metadata

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd'
        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            doc = self.target(ident_hash)

    def test_get(self):
        id, version = ('f6024d8a-1868-44c7-ab65-45419ef54881', '3')
        ident_hash = '{}@{}'.format(id, version)
        metadata = self.target(ident_hash)
        from ...utils import CNXHash
        shortid = '{}@{}'.format(CNXHash(id).get_shortid(), version)

        metadata_keys = [
            'id', 'version',
            'title', 'language', 'created', 'revised',
            'license_url', 'license_text',
            'summary', 'subjects', 'keywords',
            'cnx-archive-uri',
            # People keys
            'authors', 'editors', 'illustrators', 'publishers',
            'copyright_holders',
            # Derived from id
            'cnx-archive-shortid',
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
        self.assertEqual(metadata['cnx-archive-shortid'], shortid)

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
        self.assertIn('<span data-type="title">Atomic Masses</span>', content)

    def test_not_found(self):
        # Use a collection's id to fake this.
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'

        from cnxarchive.scripts.export_epub import ContentNotFound
        with self.assertRaises(ContentNotFound) as e:
            self.target(ident_hash)


class FileInfoGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_file_info
        return get_file_info

    def test_get(self):
        hash = '075500ad9f71890a85fe3f7a4137ac08e2b7907c'
        media_type = 'image/png'

        # In the absence of context, the file has no name
        fn, mt = self.target(hash)
        self.assertEqual(fn, hash)
        self.assertEqual(mt, media_type)

    def test_with_context(self):
        hash = '075500ad9f71890a85fe3f7a4137ac08e2b7907c'
        ident_hash = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4'
        filename = 'PhET_Icon.png'
        media_type = 'image/png'

        fn, mt = self.target(hash, context=ident_hash)
        self.assertEqual(fn, filename)
        self.assertEqual(mt, media_type)

    def test_not_found(self):
        hash = 'c7097b2e80ca7314a7f3ef58a09817f9da005570'

        from cnxarchive.scripts.export_epub import FileNotFound
        with self.assertRaises(FileNotFound) as e:
            self.target(hash)


class FileGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_file
        return get_file

    def test_get(self):
        hash = 'b7a943d679932431e674a174776397b824edc000'

        file = self.target(hash)
        self.assertEqual(file[400:414].tobytes(), 'name="license"')

    def test_not_found(self):
        hash = 'c7097b2e80ca7314a7f3ef58a09817f9da005570'

        from cnxarchive.scripts.export_epub import FileNotFound
        with self.assertRaises(FileNotFound) as e:
            self.target(hash)


class RegisteredFilesGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_registered_files
        return get_registered_files

    def test_get(self):
        ident_hash = 'f3c9ab70-a916-4d8c-9256-42953287b4e9@3'

        expected_registered_files = [
            '4c13aed36dc1cb7b2c7117d896204efc70b1c0b1',
            '8cdb49a370d8e6f503f9430a38096c8d2e3aef4f',
            'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9',
            'ee41b1074ce0abd970fcc15bbf1b6a962db1a389'
            ]

        registered_files = self.target(ident_hash)
        self.assertEqual(sorted(registered_files), expected_registered_files)

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd@4'

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            registered_files = self.target(ident_hash)

    def test_not_found_without_version(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd'

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            registered_files = self.target(ident_hash)


class TreeGetterTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import get_tree
        return get_tree

    def test_get(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'

        tree = self.target(ident_hash)

        expected_flattened_tree = [
            u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
            u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
            u'd7eb0963-6cfa-57fe-8e18-585474e8b563@7.1',
            u'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
            u'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
            u'c8bdbabc-62b1-4a5f-b291-982ab25756d7@6',
            u'5152cea8-829a-4aaf-bcc5-c58a416ecb66@7',
            u'5838b105-41cd-4c3d-a957-3ac004a48af3@5',
            u'd17ce3fa-f871-5648-81b0-46128103d61c@7.1',
            u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
            u'ea271306-f7f2-46ac-b2ec-1d80ff186a59@5',
            u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
            u'56f1c5c1-4014-450d-a477-2121e276beca@8',
            u'f6024d8a-1868-44c7-ab65-45419ef54881@3',
            u'7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2',
            u'c0a76659-c311-405f-9a99-15c71af39325@5',
            u'ae3e18de-638d-4738-b804-dc69cd4db3a3@5'
            ]
        self.assertEqual(
            [x for x in cnxepub.flatten_tree_to_ident_hashes(tree)],
            expected_flattened_tree)

    def test_not_found(self):
        ident_hash = 'f0e62639-54fc-414b-b86b-0a27d1e5de5b@4'

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            self.target(ident_hash)


class ResourceFactoryTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import resource_factory
        return resource_factory

    def test_get(self):
        hash = 'ceb4a4476591cc245e6be735399a309a224c9b67'
        ident_hash = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4'
        filename = 'index.cnxml'
        media_type = 'text/xml'

        resource = self.target(hash, context=ident_hash)

        self.assertEqual(resource.filename, filename)
        self.assertEqual(resource.media_type, media_type)
        with resource.open() as f:
            contents = f.read()
        self.assertIn('<?xml version="1.0"?>', contents)


class DocumentFactoryTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import document_factory
        return document_factory

    def test_not_found(self):
        ident_hash = '31b37e2b-9abf-4923-b2fa-de004a3cb6cd@4'
        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            doc = self.target(ident_hash)

    def test_no_context(self):
        ident_hash = '174c4069-2743-42e9-adfe-4c7084f81fc5'

        with self.assertRaises(RuntimeError) as e:
            doc = self.target(ident_hash, baked=True)

    def test_no_baked(self):
        ident_hash = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        context = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'

        from cnxarchive.scripts.export_epub import ContentNotFound
        with self.assertRaises(ContentNotFound) as e:
            doc = self.target(ident_hash, context, baked=True)

    def test_baked(self):
        ident_hash = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        context = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.2'

        doc = self.target(ident_hash, context, baked=True)

        self.assertTrue(isinstance(doc, cnxepub.Document))

        # Briefly check for the existence of metadata.
        self.assertEqual(doc.metadata['title'], u'Collated page')

        # Check for specific content.
        self.assertIn(u'<p>More tests of collated search</p>',
                      doc.content)

    def test_assembly(self):
        ident_hash = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4'
        doc = self.target(ident_hash)

        self.assertTrue(isinstance(doc, cnxepub.Document))

        # Briefly check for the existence of metadata.
        self.assertEqual(doc.metadata['title'], u'Physics: An Introduction')

        # Check for specific content.
        self.assertIn('<h3 data-type="title">Applications of Physics</h3>',
                      doc.content)

        # Check for resources
        expected_resource_filenames = [
            'Figure_01_01_01_aa.jpg', 'Figure_01_01_02_aa.jpg',
            'Figure_01_01_03_aa.jpg', 'Figure_01_01_04_aa.jpg',
            'Figure_01_01_05_aa.jpg', 'Figure_01_01_06_aa.jpg',
            'Figure_01_01_07_aa.jpg', 'Figure_01_01_08_aa.jpg',
            'Figure_01_01_09_aa.jpg', 'Figure_01_01_10_aa.jpg',
            'Figure_01_01_11_aa.jpg', 'Figure_01_01_12_aa.jpg',
            'Figure_01_01_13_aa.jpg', 'PhET_Icon.png',
            'equation-grapher_en.jar', 'index.cnxml', 'index.cnxml.html',
            'index_auto_generated.cnxml',
            ]
        self.assertEqual(len(doc.resources), 18)
        self.assertEqual(sorted([r.filename for r in doc.resources]),
                         expected_resource_filenames)

        refs = [r for r in doc.references if r.uri.startswith('/resources/')]
        # Simple check incase the data changes, otherwise not a needed test.
        self.assertEqual(len(refs), 17)
        # Check reference binding
        self.assertEqual(set([ref.is_bound for ref in refs]), set([True]))

    @testing.db_connect
    def test_resource_wo_filename(self, cursor):
        # Test for creating a document with resources that don't have filenames
        # (other than the sha1 hash), this is the case for documents published
        # using cnx-publishing
        ident_hash = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4'
        cursor.execute("""\
SELECT fileid, file FROM files NATURAL JOIN module_files NATURAL JOIN modules
WHERE ident_hash(uuid, major_version, minor_version) = %s
  AND filename = 'index.cnxml.html'""",
                       (ident_hash,))
        fileid, file_ = cursor.fetchone()
        file_ = re.sub(
            'resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png',
            'resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c',
            file_[:])

        cursor.execute("""\
UPDATE files SET file = %s WHERE fileid = %s""", (memoryview(file_), fileid))
        cursor.connection.commit()

        doc = self.target(ident_hash)

        self.assertTrue(isinstance(doc, cnxepub.Document))


class TreeToNodesTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import tree_to_nodes
        return tree_to_nodes

    def test(self):
        tree = {
            'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1',
            'shortId': None,
            'contents': [
                {'id': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 'shortId': None,
                 'title': '(title override)'},
                {'id': 'd7eb0963-6cfa-57fe-8e18-585474e8b563@7.1',
                 'shortId': '1-sJY2z6@7.1',
                 'title': None,
                 'contents': [
                     {'id': 'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
                      'shortId': '88mrcKkW@3',
                      'title': '(another title override)'},
                     {'id': 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
                      'shortId': '05W1Zl_j@4',
                      'title': 'Physics: An Introduction'}]}]}
        nodes = self.target(tree)

        self.assertEqual(
            cnxepub.model_to_tree(nodes[0]),
            {'id': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
             'shortId': 'IJ3rHxpG@7',
             'title': '(title override)'}
            )
        self.assertEqual(
            cnxepub.model_to_tree(nodes[1]),
            tree['contents'][1]
            )


class BinderFactoryTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import binder_factory
        return binder_factory

    def test_not_found(self):
        ident_hash = 'f0e62639-54fc-414b-b86b-0a27d1e5de5b'
        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            binder = self.target(ident_hash)

    def test_no_baked(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'

        from cnxarchive.scripts.export_epub import NotFound
        with self.assertRaises(NotFound) as e:
            binder = self.target(ident_hash, baked=True)

    def test_baked(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.2'
        binder = self.target(ident_hash, baked=True)

        # Briefly check for the existence of metadata.
        self.assertEqual(binder.metadata['title'], u'College Physics')

        # Check for containment

        expected_tree = {
            'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@6.2',
            'shortId': '55_943-0@6.2',
            'title': u'College Physics',
            'contents': [
                {'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 'shortId': u'IJ3rHxpG@7',
                 'title': u'New Preface'},
                {'id': u'174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                 'shortId': u'F0xAaSdD@1',
                 'title': u'Other Composite'}
                ],
            }

        self.assertEqual(cnxepub.model_to_tree(binder), expected_tree)

    def test_assembly(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'
        binder = self.target(ident_hash)

        # Briefly check for the existence of metadata.
        self.assertEqual(binder.metadata['title'], u'College Physics')

        # Check for containment
        expected_tree = {
            'shortId': '55_943-0@7.1',
            'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
            'title': u'College Physics',
            'contents': [
                {'shortId': u'IJ3rHxpG@7',
                 'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 'title': u'Preface'},
                {
                 'id': u'd7eb0963-6cfa-57fe-8e18-585474e8b563@7.1',
                 'shortId': u'1-sJY2z6@7.1',
                 'title': u'Introduction: The Nature of Science and Physics',
                 'contents': [
                    {'shortId': u'88mrcKkW@3',
                     'id': u'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
                     'title': u'Introduction to Science and the Realm of Physics, Physical Quantities, and Units'},
                    {'shortId': u'05W1Zl_j@4',
                     'id': u'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
                     'title': u'Physics: An Introduction'},
                    {'shortId': u'yL26vGKx@6',
                     'id': u'c8bdbabc-62b1-4a5f-b291-982ab25756d7@6',
                     'title': u'Physical Quantities and Units'},
                    {'shortId': u'UVLOqIKa@7',
                     'id': u'5152cea8-829a-4aaf-bcc5-c58a416ecb66@7',
                     'title': u'Accuracy, Precision, and Significant Figures'},
                    {'shortId': u'WDixBUHN@5',
                     'id': u'5838b105-41cd-4c3d-a957-3ac004a48af3@5',
                     'title': u'Approximation'}]},
                    {'shortId': u'0Xzj-vhx@7.1',
                     'id': u'd17ce3fa-f871-5648-81b0-46128103d61c@7.1',
                     'title': u"Further Applications of Newton's Laws: Friction, Drag, and Elasticity",
                     'contents': [
                        {'shortId': u'JKLtEyKm@2',
                         'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                         'title': u'Introduction: Further Applications of Newton\u2019s Laws'},
                        {'shortId': u'6icTBvfy@5',
                         'id': u'ea271306-f7f2-46ac-b2ec-1d80ff186a59@5',
                         'title': u'Friction'},
                        {'shortId': u'JjRqQoS5@6',
                         'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                         'title': u'Drag Forces'},
                        {'shortId': u'VvHFwUAU@8',
                         'id': u'56f1c5c1-4014-450d-a477-2121e276beca@8',
                         'title': u'Elasticity: Stress and Strain'}], },
                {'shortId': u'9gJNihho@3',
                 'id': u'f6024d8a-1868-44c7-ab65-45419ef54881@3',
                 'title': u'Atomic Masses'},
                {'shortId': u'clA4axSn@2',
                 'id': u'7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2',
                 'title': u'Selected Radioactive Isotopes'},
                {'shortId': u'wKdmWcMR@5',
                 'id': u'c0a76659-c311-405f-9a99-15c71af39325@5',
                 'title': u'Useful Inf\xf8rmation'},
                {'shortId': u'rj4Y3mON@5',
                 'id': u'ae3e18de-638d-4738-b804-dc69cd4db3a3@5',
                 'title': u'Glossary of Key Symbols and Notation'}],
        }

        self.maxDiff = None
        self.assertEqual(cnxepub.model_to_tree(binder), expected_tree)

        # Check translucent binder metadata
        translucent_binder = binder[1]
        self.assertTrue(
            isinstance(translucent_binder, cnxepub.TranslucentBinder))
        expected_metadata = {
            'id': u'd7eb0963-6cfa-57fe-8e18-585474e8b563@7.1',
            'shortId': u'1-sJY2z6@7.1',
            'title': 'Introduction: The Nature of Science and Physics',
            }
        for k, v in expected_metadata.items():
            self.assertEqual(translucent_binder.metadata[k], v)


class FactoryFactoryTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import factory
        return factory

    def test_document(self):
        ident_hash = 'c0a76659-c311-405f-9a99-15c71af39325@5'
        model = self.target(ident_hash)
        self.assertTrue(isinstance(model, cnxepub.Document))

    def test_binder(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'
        model = self.target(ident_hash)
        self.assertTrue(isinstance(model, cnxepub.Binder))


class EpubCreationTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub import create_epub
        return create_epub

    @property
    def filepath(self):
        filepath = getattr(self, '_filepath', None)
        if filepath is None:
            _, filepath = tempfile.mkstemp('.epub')
            self._filepath = filepath
            self.addCleanup(delattr, self, '_filepath')
        return filepath

    def test_document(self):
        ident_hash = 'c0a76659-c311-405f-9a99-15c71af39325@5'
        model = self.target(ident_hash, self.filepath)

        with zipfile.ZipFile(self.filepath, 'r') as zf:
            # Check for select files
            expected_to_contain = [
                'contents/c0a76659-c311-405f-9a99-15c71af39325@5.xhtml',
                'resources/0b313a1dfc181e4e5c4c86832d99e16e0fecfb20',
                'resources/4bfac6b2934befce939cb70321bba1fb414543b5',
                'resources/1ce555936346f79c7589f70cef8eef9f83b13570'
                ]
            self.assert_contains(zf.namelist(), expected_to_contain)

    def test_binder(self):
        ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'
        model = self.target(ident_hash, self.filepath)

        with zipfile.ZipFile(self.filepath, 'r') as zf:
            # Check for select files
            expected_to_contain = [
                'contents/e79ffde3-7fb4-4af3-9ec8-df648b391597.xhtml',
                'contents/56f1c5c1-4014-450d-a477-2121e276beca@8.xhtml',
                'e79ffde3-7fb4-4af3-9ec8-df648b391597.opf',
                'resources/0b313a1dfc181e4e5c4c86832d99e16e0fecfb20',
                ]
            self.assert_contains(zf.namelist(), expected_to_contain)


class MainTestCase(BaseTestCase):

    @property
    def target(self):
        from cnxarchive.scripts.export_epub.main import main
        return main

    def setUp(self):
        pass

    def tearDown(self):
        pass

    collection_ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1'
    module_ident_hash = 'c0a76659-c311-405f-9a99-15c71af39325@5'

    def test_success_output_for_collection(self):
        _, filepath = tempfile.mkstemp('.epub')
        # Call the command line script.
        args = (testing.config_uri(), self.collection_ident_hash, filepath)
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        with zipfile.ZipFile(filepath, 'r') as zf:
            # Check for select files
            expected_to_contain = [
                'contents/e79ffde3-7fb4-4af3-9ec8-df648b391597.xhtml',
                'contents/56f1c5c1-4014-450d-a477-2121e276beca@8.xhtml',
                'e79ffde3-7fb4-4af3-9ec8-df648b391597.opf',
                'resources/0b313a1dfc181e4e5c4c86832d99e16e0fecfb20',
                ]
            self.assert_contains(zf.namelist(), expected_to_contain)

    def test_success_output_for_module(self):
        _, filepath = tempfile.mkstemp('.epub')
        # Call the command line script.
        args = (testing.config_uri(), self.module_ident_hash, filepath)
        return_code = self.target(args)
        self.assertEqual(return_code, 0)

        with zipfile.ZipFile(filepath, 'r') as zf:
            # Check for select files
            expected_to_contain = [
                'contents/c0a76659-c311-405f-9a99-15c71af39325@5.xhtml',
                'resources/0b313a1dfc181e4e5c4c86832d99e16e0fecfb20',
                'resources/4bfac6b2934befce939cb70321bba1fb414543b5',
                'resources/1ce555936346f79c7589f70cef8eef9f83b13570',
                ]
            self.assert_contains(zf.namelist(), expected_to_contain)

    def test_failure_using_stdout(self):
        args = (testing.config_uri(), self.module_ident_hash, '-')
        with self.assertRaises(RuntimeError) as e:
            self.target(args)
            self.assertIn('stdout', e.args[0])
