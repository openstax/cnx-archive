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
from io import BytesIO

import psycopg2

from . import postgresql_fixture


here = os.path.abspath(os.path.dirname(__file__))
TESTING_DATA_DIR = os.path.join(here, 'data')
TESTING_LEGACY_DATA_SQL_FILE = os.path.join(TESTING_DATA_DIR,
                                            'legacy-data.sql')


class TransformTests(unittest.TestCase):

    maxDiff = 40000

    def test_cnxml_to_html(self):
        # Case to test the transformation of cnxml to html.
        # FIXME This transformation shouldn't even be in this package.

        index_xml_filepath = os.path.join(TESTING_DATA_DIR,
                                          'm42033-1.3.cnxml')
        index_html_filepath = os.path.join(TESTING_DATA_DIR,
                                           'm42033-1.3.html')

        with open(index_xml_filepath, 'r') as fp:
            index_xml = fp.read()
        from ..to_html import transform_cnxml_to_html
        index_html = transform_cnxml_to_html(index_xml)

        with open(index_html_filepath, 'r') as fp:
            expected_result = fp.read()
        self.assertMultiLineEqual(index_html, expected_result)


class ToHtmlTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        cls.connection_string = cls.fixture._connection_string
        cls._db_connection = psycopg2.connect(cls.connection_string)

    @classmethod
    def tearDownClass(cls):
        cls._db_connection.close()

    def setUp(self):
        self.fixture.setUp()
        # Load the database with example legacy data.
        with self._db_connection.cursor() as cursor:
            with open(TESTING_LEGACY_DATA_SQL_FILE, 'rb') as fp:
                cursor.execute(fp.read())
        self._db_connection.commit()

    def tearDown(self):
        self.fixture.tearDown()

    # def test_collection_transform(self):
    #     # Case to test for a successful tranformation of a collection from
    #     #   collxml to html.
    #     from ..to_html import produce_html_for_collections
    #     with psycopg2.connect(self.connection_string) as db_connection:
    #         iterator = produce_html_for_collections(db_connection)
    #         collection_id, message = iterator.next()
    #         db_connection.commit()

    #     with psycopg2.connect(self.connection_string) as db_connection:
    #         with db_connection.cursor() as cursor:
    #             cursor.execute("SELECT file FROM files "
    #                            "  WHERE fileid = "
    #                            "    (SELECT fileid FROM module_files "
    #                            "       WHERE module_ident = %s "
    #                            "         AND filename = 'collection.html');",
    #                            (collection_id,))
    #             collection_html = cursor.fetchone()[0][:]
    #     # We only need to test that the file got transformed and placed
    #     #   placed in the database, the transform itself should be verified.
    #     #   independent of this code.
    #     self.assertTrue(collection_html.find('<html') >= 0)

    # def test_collection_transform_w_invalid_data(self):
    #     # Case to test for an unsuccessful tranformation of a collection from
    #     #   collxml to html.
    #     pass

    # def test_collection_transform_exists(self):
    #     # Case to test for a successful tranformation with an existing
    #     #   transform from collxml to html has already been done.
    #     pass

    def test_module_transform(self):
        # Case to test for a successful tranformation of a module from
        #   cnxml to html.
        from ..to_html import produce_html_for_modules
        with psycopg2.connect(self.connection_string) as db_connection:
            values = [v for v in produce_html_for_modules(db_connection)]
            db_connection.commit()

        ident = 2  # m42955
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT file FROM files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = 'index.html');",
                               (ident,))
                index_html = cursor.fetchone()[0][:]
        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertTrue(index_html.find('<html') >= 0)

    def test_module_transform_exists(self):
        pass

    def test_module_transform_w_invalid_data(self):
        # Case to test for an unsuccessful transformation of a module from
        #   cnxml to html.
        ident = 2  # m42955
        # Hack a chunk out of the file to ensure it fails.
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT file from files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = 'index.cnxml');",
                               (ident,))
                index_cnxml = cursor.fetchone()[0][:]
                # Make a mess of things...
                content = index_cnxml[:600] + index_cnxml[700:]
                payload = (psycopg2.Binary(content), ident,)
                cursor.execute("UPDATE files SET file = %s "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = 'index.cnxml');",
                               payload)
            db_connection.commit()

        from ..to_html import produce_html_for_modules
        with psycopg2.connect(self.connection_string) as db_connection:
            values = [v for v in produce_html_for_modules(db_connection)]
            db_connection.commit()

        message_dict = dict(values)
        self.assertIsNotNone(message_dict[ident])
        self.assertEqual(message_dict[ident],
                         u"Failed to parse QName 'md:tit47:', " \
                             "line 11, column 12")

    def test_module_transform_of_references(self):
        # Case to test that a document's internal references have
        #   been rewritten to the cnx-archive's read-only API routes.

        ident = 3
        from ..to_html import (
            fix_reference_urls, transform_cnxml_to_html)
        with psycopg2.connect(self.connection_string) as db_connection:
            content_filepath = os.path.join(TESTING_DATA_DIR,
                                            'm42119-1.3-modified.cnxml')
            with open(content_filepath, 'r') as fb:
                content = transform_cnxml_to_html(fb.read())
                content = BytesIO(content)
                content = fix_reference_urls(db_connection, ident, content)

        # Read the content for the reference changes.
        expected_img_ref = '<img src="../resources/38b5477eb68417a65d7fcb1bc1d6630e" data-mime-type="image/jpg" alt="The spiral galaxy Andromeda is shown."/>'
        self.assertTrue(content.find(expected_img_ref) >= 0)
        expected_internal_ref = '<a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@1.7">'
        self.assertTrue(content.find(expected_internal_ref) >= 0)
        expected_resource_ref = '<a href="../resources/38b5477eb68417a65d7fcb1bc1d6630e">'
        self.assertTrue(content.find(expected_resource_ref) >= 0)
