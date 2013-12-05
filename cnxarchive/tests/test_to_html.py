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
import re

import psycopg2

from . import postgresql_fixture


here = os.path.abspath(os.path.dirname(__file__))
TESTING_DATA_DIR = os.path.join(here, 'data')
TESTING_DATA_SQL_FILE = os.path.join(TESTING_DATA_DIR, 'data.sql')
TESTING_LEGACY_DATA_SQL_FILE = os.path.join(TESTING_DATA_DIR,
                                            'legacy-data.sql')


class TransformTests(unittest.TestCase):

    maxDiff = 40000

    def call_target(self, *args, **kwargs):
        from ..to_html import transform_cnxml_to_html
        return transform_cnxml_to_html(*args, **kwargs)

    def get_file(self, filename):
        path = os.path.join(TESTING_DATA_DIR, filename)
        with open(path, 'r') as fp:
            return fp.read()

        # Case to test the transformation of cnxml to html.
        # FIXME This transformation shouldn't even be in this package.

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        cnxml = self.get_file('m42033-1.3.cnxml')
        html = self.get_file('m42033-1.3.html')

        content = self.call_target(cnxml)

        self.assertMultiLineEqual(content, html)

    def test_module_transform_entity_expansion(self):
        # Case to test that a document's internal entities have been
        #   deref'ed from the DTD and expanded
        cnxml = self.get_file('m10761-2.3.cnxml')

        content = self.call_target(cnxml)

        # &#995; is expansion of &lambda;
        self.assertTrue(content.find('&#955;') >= 0)

    def test_module_transform_image_with_print_width(self):
        cnxml = self.get_file('m31947-1.3.cnxml')

        content = self.call_target(cnxml)

        # Assert <img> tag is generated
        img = re.search('(<img [^>]*>)', content)
        self.assertTrue(img is not None)
        img = img.group(1)
        self.assertTrue('src="graphics1.jpg"' in img)
        self.assertTrue('data-print-width="6.5in"' in img)


class AbstractToHtmlTestCase(unittest.TestCase):
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
            with open(TESTING_DATA_SQL_FILE, 'rb') as fp:
                cursor.execute(fp.read())
                cursor.execute("UPDATE abstracts SET (html) = (null);")
        self._db_connection.commit()

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from ..to_html import produce_html_for_abstract
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                return produce_html_for_abstract(db_connection, cursor,
                                                 *args, **kwargs)

    def test_success(self):
        # Case to test for a successful tranformation of an abstract from
        #   cnxml to html.
        document_ident, abstractid = 2, 2  # m42955
        self.call_target(document_ident)

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT html FROM abstracts "
                               "  WHERE abstractid = %s;",
                               (abstractid,))
                html = cursor.fetchone()[0]
        transformed_contents = '<ul class="list"><li class="item">one</li><li class="item">two</li><li class="item">three</li></ul>'
        self.assertTrue(html.find(transformed_contents) >= 0)

    def test_success_w_reference(self):
        # Case with an abstract containing an internal reference.
        document_ident, abstractid = 3, 3
        self.call_target(document_ident)

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT html FROM abstracts "
                               "  WHERE abstractid = %s;",
                               (abstractid,))
                html = cursor.fetchone()[0]
        expected = 'href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce@1.4"'
        self.assertTrue(html.find(expected) >= 0)

    def test_success_w_cnxml_root_element(self):
        # Case with an abstract that contains an outter xml element
        #   (e.g. <para>).
        document_ident, abstractid = 4, 4
        self.call_target(document_ident)

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT html FROM abstracts "
                               "  WHERE abstractid = %s;",
                               (abstractid,))
                html = cursor.fetchone()[0]
        transformed_contents = '<p class="para">A link to the <a href="http://example.com">outside world</a>.</p>'
        self.assertTrue(html.find(transformed_contents) >= 0)

    def test_success_w_no_cnxml(self):
        # Case that ensures plaintext abstracts get wrapped with xml
        #   and include the various namespaces.
        document_ident, abstractid = 5, 5
        self.call_target(document_ident)

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT html FROM abstracts "
                               "  WHERE abstractid = %s;",
                               (abstractid,))
                html = cursor.fetchone()[0]
        transformed_contents = 'A rather short plaintext abstract.</div>'
        # Check for the ending wrapper tag, but not the initial one, because
        #   the namespaces are unordered and can't reliably be tested.
        self.assertTrue(html.find(transformed_contents) >= 0)

    def test_success_w_empty(self):
        # Case that ensures an empty abstract is saved as an empty html
        #   entry.
        document_ident, abstractid = 6, 6
        self.call_target(document_ident)

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT html FROM abstracts "
                               "  WHERE abstractid = %s;",
                               (abstractid,))
                html = cursor.fetchone()[0]
        self.assertEqual(html, None)

    def test_failure_on_nonexistent_document(self):
        # Case to ensure failure the requested document doesn't exist.
        document_ident, abstractid = 50, 50

        with self.assertRaises(ValueError) as caught_exception:
            self.call_target(document_ident)
        exception = caught_exception.exception
        # Just ensure that we aren't blind when the exception is raised.
        self.assertTrue(exception.message.find(str(document_ident)) >= 0)

    def test_failure_on_missing_abstract(self):
        # Case to ensure failure when an abstract is missing.
        document_ident, abstractid = 5, 5
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("UPDATE modules SET (abstractid) = (null) "
                               "WHERE module_ident = %s;",
                               (document_ident,))
                cursor.execute("DELETE FROM abstracts WHERE abstractid = %s;",
                               (abstractid,))

        from ..to_html import MissingAbstract
        with self.assertRaises(MissingAbstract) as caught_exception:
            self.call_target(document_ident)


class ModuleToHtmlTestCase(unittest.TestCase):
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

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from ..to_html import produce_html_for_module
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                return produce_html_for_module(db_connection, cursor,
                                               *args, **kwargs)

    def test_cnxml_source_missing(self):
        # Case to test that we catch/raise exceptions when the source
        #   CNXML file for a document can't be found.
        ident, filename = 2, 'index.cnxml'
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DELETE FROM module_files "
                               "WHERE module_ident = %s AND filename = %s;",
                               (ident, filename,))
            db_connection.commit()

        from ..to_html import MissingDocumentOrSource
        with self.assertRaises(MissingDocumentOrSource) as caught_exc:
            self.call_target(ident, filename)
        exception = caught_exc.exception

        self.assertEqual(exception.document_ident, ident)
        self.assertEqual(exception.filename, filename)

    def test_missing_document(self):
        # Case to test that we catch/raise exceptions when the document
        #   can't be found.
        ident, filename = 0, 'index.cnxml'

        from ..to_html import MissingDocumentOrSource
        with self.assertRaises(MissingDocumentOrSource) as caught_exc:
            self.call_target(ident, filename)
        exception = caught_exc.exception

        self.assertEqual(exception.document_ident, ident)
        self.assertEqual(exception.filename, filename)

    def test_success(self):
        # Case to test for a successful tranformation of a module from
        #   cnxml to html.
        ident, filename = 2, 'index.cnxml'  # m42955
        self.call_target(ident)

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

    def test_module_transform_remove_index_html(self):
        # Test when overwrite_html is True, the index.html is removed from the
        # database before a new one is added

        # Create an index.html for module_ident 2
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute('INSERT INTO files (file) '
                               '(SELECT file FROM files WHERE fileid = 1) '
                               'RETURNING fileid')
                fileid = cursor.fetchone()[0]
                cursor.execute('INSERT INTO module_files VALUES (2, DEFAULT,'
                               "%s, 'index.html', 'text/html')", (fileid,))
            db_connection.commit()

        msg = self.call_target(2, overwrite_html=True)

        # Assert there are no error messages
        self.assertEqual(msg, None)

        # Check cnxml is transformed to html
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT fileid, file FROM files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = 2 "
                               "         AND filename = 'index.html');")
                index_html_id, index_html = cursor.fetchone()
                index_html = index_html[:]
        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertTrue(index_html.find('<html') >= 0)

        # Assert index.html has been replaced
        self.assertNotEqual(fileid, index_html_id)

    def test_module_transform_index_html_exists(self):
        # Test when overwrite_html is False, the index.html causes an error when a
        # new one is generated

        # Create an index.html for module_ident 2
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute('INSERT INTO files (file) '
                               'SELECT file FROM files WHERE fileid = 1 '
                               'RETURNING fileid')
                fileid = cursor.fetchone()[0]
                cursor.execute('INSERT INTO module_files VALUES (2, DEFAULT,'
                               "%s, 'index.html', 'text/html')", (fileid,))
            db_connection.commit()

        from ..to_html import IndexHtmlExistsError

        with self.assertRaises(IndexHtmlExistsError) as e:
            self.call_target(2, overwrite_html=False)

        # Check the error message
        self.assertEqual(e.exception.message,
                         'index.html already exists for document 2')

        # Assert index.html is not deleted
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT fileid FROM files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = 2 "
                               "         AND filename = 'index.html');")
                index_html_id = cursor.fetchone()[0]

        self.assertEqual(fileid, index_html_id)

    def _make_document_data_invalid(self, ident=2, filename='index.cnxml'):
        """Hacks a chunk out of the file given as ``filename``
        at module with the given ``ident``.
        This to ensure a transform failure.
        """
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT file from files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = %s);",
                               (ident, filename))
                index_cnxml = cursor.fetchone()[0][:]
                # Make a mess of things...
                content = index_cnxml[:600] + index_cnxml[700:]
                payload = (psycopg2.Binary(content), ident, filename,)
                cursor.execute("UPDATE files SET file = %s "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = %s);",
                               payload)
            db_connection.commit()
        return ident

    def test_transform_w_invalid_data(self):
        # Case to test for an unsuccessful transformation of a module.
        #   The xml is invalid, therefore the transform cannot succeed.
        ident = self._make_document_data_invalid()

        with self.assertRaises(Exception) as caught_exc:
            self.call_target(ident)

        exception = caught_exc.exception
        from lxml.etree import XMLSyntaxError
        self.assertTrue(isinstance(exception, XMLSyntaxError))
        self.assertEqual(
                exception.message,
                u"Failed to parse QName 'md:tit47:', line 11, column 12")


class ReferenceResolutionTestCase(unittest.TestCase):
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

    def test_reference_rewrites(self):
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
                content, bad_refs = fix_reference_urls(db_connection, ident, content)

        # Read the content for the reference changes.
        expected_img_ref = '<img src="/resources/38b5477eb68417a65d7fcb1bc1d6630e" data-media-type="image/jpg" alt="The spiral galaxy Andromeda is shown."/>'
        self.assertTrue(content.find(expected_img_ref) >= 0)
        expected_internal_ref = '<a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@1.7">'
        self.assertTrue(content.find(expected_internal_ref) >= 0)
        expected_resource_ref = '<a href="/resources/38b5477eb68417a65d7fcb1bc1d6630e">'
        self.assertTrue(content.find(expected_resource_ref) >= 0)

