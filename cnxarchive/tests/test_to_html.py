# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys
import re
import unittest
from io import BytesIO

from lxml import etree
import psycopg2

from . import testing


class TransformTests(unittest.TestCase):

    maxDiff = 40000

    def call_target(self, *args, **kwargs):
        from ..to_html import transform_cnxml_to_html
        return transform_cnxml_to_html(*args, **kwargs)

    def get_file(self, filename):
        path = os.path.join(testing.DATA_DIRECTORY, filename)
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
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def call_target(self, cursor, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from ..to_html import produce_html_for_abstract
        return produce_html_for_abstract(cursor.connection, cursor,
                                         *args, **kwargs)

    @testing.db_connect
    def test_success(self, cursor):
        # Case to test for a successful tranformation of an abstract from
        #   cnxml to html.
        document_ident, abstractid = 2, 2  # m42955
        self.call_target(document_ident)

        cursor.execute("SELECT html FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        html = cursor.fetchone()[0]
        expected = '<ul><li>one</li><li>two</li><li>three</li></ul>'
        self.assertTrue(html.find(expected) >= 0)

    @testing.db_connect
    def test_success_w_reference(self, cursor):
        # Case with an abstract containing an internal reference.
        document_ident, abstractid = 3, 3
        self.call_target(document_ident)

        cursor.execute("SELECT html FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        html = cursor.fetchone()[0]
        expected = 'href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce@4"'
        self.assertTrue(html.find(expected) >= 0)

    @testing.db_connect
    def test_success_w_cnxml_root_element(self, cursor):
        # Case with an abstract that contains an outter xml element
        #   (e.g. <para>).
        document_ident, abstractid = 4, 4
        self.call_target(document_ident)

        cursor.execute("SELECT html FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        html = cursor.fetchone()[0]
        expected = '<p>A link to the <a href="http://example.com">outside world</a>.</p>'
        self.assertTrue(html.find(expected) >= 0)

    @testing.db_connect
    def test_success_w_no_cnxml(self, cursor):
        # Case that ensures plaintext abstracts get wrapped with xml
        #   and include the various namespaces.
        document_ident, abstractid = 5, 5
        self.call_target(document_ident)

        cursor.execute("SELECT html FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        html = cursor.fetchone()[0]
        expected = 'A rather short plaintext abstract.</div>'
        # Check for the ending wrapper tag, but not the initial one, because
        #   the namespaces are unordered and can't reliably be tested.
        self.assertTrue(html.find(expected) >= 0)

    @testing.db_connect
    def test_success_w_empty(self, cursor):
        # Case that ensures an empty abstract is saved as an empty html
        #   entry.
        document_ident, abstractid = 6, 6
        self.call_target(document_ident)

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

    @testing.db_connect
    def test_failure_on_missing_abstract(self, cursor):
        # Case to ensure failure when an abstract is missing.
        document_ident, abstractid = 5, 5
        cursor.execute("UPDATE modules SET (abstractid) = (null) "
                       "WHERE module_ident = %s;",
                       (document_ident,))
        cursor.execute("DELETE FROM abstracts WHERE abstractid = %s;",
                       (abstractid,))
        cursor.connection.commit()

        from ..to_html import MissingAbstract
        with self.assertRaises(MissingAbstract) as caught_exception:
            self.call_target(document_ident)


class ModuleToHtmlTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def call_target(self, cursor, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from ..to_html import produce_html_for_module
        return produce_html_for_module(cursor.connection, cursor,
                                       *args, **kwargs)

    @testing.db_connect
    def test_cnxml_source_missing(self, cursor):
        # Case to test that we catch/raise exceptions when the source
        #   CNXML file for a document can't be found.
        ident, filename = 2, 'index.cnxml'
        cursor.execute("DELETE FROM module_files "
                       "WHERE module_ident = %s AND filename = %s;",
                       (ident, filename,))
        cursor.connection.commit()

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

    @testing.db_connect
    def test_success(self, cursor):
        # Case to test for a successful tranformation of a module from
        #   cnxml to html.
        ident, filename = 2, 'index.cnxml'  # m42955

        # Delete module_ident 2 index.cnxml.html
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename = 'index.cnxml.html'")
        cursor.connection.commit()
        self.call_target(ident)

        cursor.execute("SELECT file FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = %s "
                       "         AND filename = 'index.cnxml.html');",
                       (ident,))
        index_html = cursor.fetchone()[0][:]

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertTrue(index_html.find('<html') >= 0)

    @testing.db_connect
    def test_module_transform_remove_index_html(self, cursor):
        # Test when overwrite_html is True, the index.cnxml.html is removed
        # from the database before a new one is added

        # Create an index.cnxml.html for module_ident 2
        # Delete module_ident 2 index.cnxml.html
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename = 'index.cnxml.html'")

        cursor.execute('INSERT INTO files (file) '
                       '(SELECT file FROM files WHERE fileid = 1) '
                       'RETURNING fileid')
        fileid = cursor.fetchone()[0]
        cursor.execute('INSERT INTO module_files VALUES (2, DEFAULT,'
                       "%s, 'index.cnxml.html', 'text/html')", (fileid,))
        cursor.connection.commit()

        msg = self.call_target(2, overwrite_html=True)

        # Assert there are no error messages
        self.assertEqual(msg, None)

        # Check cnxml is transformed to html
        cursor.execute("SELECT fileid, file FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = 2 "
                       "         AND filename = 'index.cnxml.html');")
        index_html_id, index_html = cursor.fetchone()
        index_html = index_html[:]

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertTrue(index_html.find('<html') >= 0)

        # Assert index.html has been replaced
        self.assertNotEqual(fileid, index_html_id)

    @testing.db_connect
    def test_module_transform_index_html_exists(self, cursor):
        # Test when overwrite_html is False, the index.cnxml.html causes an
        # error when a new one is generated

        # Create an index.cnxml.html for module_ident 2
        # Delete module_ident 2 index.cnxml.html
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename = 'index.cnxml.html'")

        cursor.execute('INSERT INTO files (file) '
                       'SELECT file FROM files WHERE fileid = 1 '
                       'RETURNING fileid')
        fileid = cursor.fetchone()[0]
        cursor.execute('INSERT INTO module_files VALUES (2, DEFAULT,'
                       "%s, 'index.cnxml.html', 'text/html')", (fileid,))
        cursor.connection.commit()

        from ..to_html import IndexHtmlExistsError

        with self.assertRaises(IndexHtmlExistsError) as e:
            self.call_target(2, overwrite_html=False)

        # Check the error message
        self.assertEqual(e.exception.message,
                         'index.cnxml.html already exists for document 2')

        # Assert index.cnxml.html is not deleted
        cursor.execute("SELECT fileid FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = 2 "
                       "         AND filename = 'index.cnxml.html');")
        index_html_id = cursor.fetchone()[0]

        self.assertEqual(fileid, index_html_id)

    @testing.db_connect
    def _make_document_data_invalid(self, cursor, ident=2,
                                    filename='index.cnxml'):
        """Hacks a chunk out of the file given as ``filename``
        at module with the given ``ident``.
        This to ensure a transform failure.
        """
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
        return ident

    @testing.db_connect
    def test_transform_w_invalid_data(self, cursor):
        # Case to test for an unsuccessful transformation of a module.
        #   The xml is invalid, therefore the transform cannot succeed.
        ident = self._make_document_data_invalid()

        # Delete ident index.cnxml.html
        cursor.execute('DELETE FROM module_files WHERE '
                       'module_ident = %s AND filename = %s',
                       [ident, 'index.cnxml.html'])
        cursor.connection.commit()

        with self.assertRaises(Exception) as caught_exc:
            self.call_target(ident)

        exception = caught_exc.exception
        from lxml.etree import XMLSyntaxError
        self.assertTrue(isinstance(exception, XMLSyntaxError))
        self.assertEqual(
                exception.message,
                u"Failed to parse QName 'md:tit47:', line 11, column 12")


class ReferenceResolutionTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()
        self.fixture.setUpAccountsDb()
        from .. import _set_settings
        settings = testing.integration_test_settings()
        _set_settings(settings)

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def test_reference_rewrites(self, cursor):
        # Case to test that a document's internal references have
        #   been rewritten to the cnx-archive's read-only API routes.
        ident = 3
        from ..to_html import (
            fix_reference_urls, transform_cnxml_to_html)
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm42119-1.3-modified.cnxml')
        with open(content_filepath, 'r') as fb:
            content = transform_cnxml_to_html(fb.read())
            content = BytesIO(content)
            content, bad_refs = fix_reference_urls(cursor.connection, ident,
                                                   content)

        # Read the content for the reference changes.
        expected_img_ref = '<img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" data-media-type="image/jpg" alt="The spiral galaxy Andromeda is shown."/>'
        self.assertTrue(content.find(expected_img_ref) >= 0)
        expected_internal_ref = '<a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7">'
        self.assertTrue(content.find(expected_internal_ref) >= 0)
        expected_resource_ref = '<a href="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg">'
        self.assertTrue(content.find(expected_resource_ref) >= 0)

    @testing.db_connect
    def test_reference_not_parseable(self, cursor):
        ident = 3
        from ..to_html import (
                fix_reference_urls, transform_cnxml_to_html)
        import glob
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm45070.cnxml')
        with open(content_filepath, 'r') as fb:
            content = transform_cnxml_to_html(fb.read())
            content = BytesIO(content)
            content, bad_refs = fix_reference_urls(cursor.connection, ident,
                                                   content)

        self.assertEqual(bad_refs, [
            "Missing resource with filename 'InquiryQuestions.svg', moduleid None version None.: document=3, reference=InquiryQuestions.svg",
            "Invalid reference value: document=3, reference=/m",
            "Unable to find a reference to 'm43540' at version 'None'.: document=3, reference=/m43540",
            ])
        self.assertTrue('<a href="/m">' in content)

    @testing.db_connect
    def test_reference_resolver(self, cursor):
        from ..to_html import ReferenceResolver

        self.maxDiff = None
        self.addCleanup(delattr, self, 'maxDiff')

        html = BytesIO('''\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/m42092#xn">
            <img src="Figure_01_00_01.jpg"/>
        </a>
        <a href="/ m42709@1.4">
            <img src="/Figure_01_00_01.jpg"/>
        </a>
        <a href="/m42092/latest?collection=col11406/latest#figure">
            Module link with collection
        </a>
        <a href="/m42955/latest?collection=col11406/1.6">
            Module link with collection and version
        </a>
        <img src=" Figure_01_00_01.jpg"/>
        <img src="/content/m42092/latest/PhET_Icon.png"/>
        <img src="/content/m42092/1.4/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="Figure_01_00_01.jpg"/>

        <audio src="Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"></audio>

        <video src="Figure_01_00_01.jpg" id="music" mime-type="video/mp4"></video>

        <object width="400" height="400" data="Figure_01_00_01.jpg"></object>

        <object width="400" height="400">
            <embed src="Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>''')

        resolver = ReferenceResolver(cursor.connection, 3, html)
        html, bad_references = resolver()
        cursor.connection.commit()

        self.assertEqual(bad_references, [
            "Missing resource with filename 'PhET_Icon.png', moduleid m42092 version 1.3.: document=3, reference=PhET_Icon.png",
            ])
        self.assertMultiLineEqual(html, '''\
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce@4#xn">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/ae3e18de-638d-4738-b804-dc69cd4db3a3@4">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597:d395b566-5fe3-4428-bcb2-19016e3aa3ce#figure">
            Module link with collection
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1:209deb1f-1a46-4369-9e0d-18674cf58a3e">
            Module link with collection and version
        </a>
        <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <audio src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"/>

        <video src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="video/mp4"/>

        <object width="400" height="400" data="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <object width="400" height="400">
            <embed src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>''')


    @testing.db_connect
    def test_get_resource_info(self, cursor):
        from ..to_html import ReferenceResolver, ReferenceNotFound

        resolver = ReferenceResolver(cursor.connection, 3,
                                     BytesIO('<html></html>'))

        # Test file not found
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png')

        # Test getting a file in module 3
        self.assertEqual(resolver.get_resource_info('Figure_01_00_01.jpg'),
                {'hash': 'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9', 'id': 6})

        # Test file not found outside of module 3
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png', document_id='m42955')

        # Test getting a file in another module
        self.assertEqual(resolver.get_resource_info('PhET_Icon.png',
            document_id='m42092'),
            {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c', 'id': 23})

        # Test file not found with version
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png', document_id='m42092',
                          version='1.3')

        # Test getting a file with version
        self.assertEqual(resolver.get_resource_info('PhET_Icon.png',
            document_id='m42092', version='1.4'),
            {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c', 'id': 23})

    def test_parse_reference(self):
        from ..to_html import (parse_reference, MODULE_REFERENCE,
                RESOURCE_REFERENCE)

        self.assertEqual(parse_reference('/m12345'),
                (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        self.assertEqual(parse_reference('/content/m12345'),
                (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        self.assertEqual(parse_reference('http://cnx.org/content/m12345'),
                (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        # m10278 "The Advanced CNXML"
        self.assertEqual(parse_reference('/m9007'),
                (MODULE_REFERENCE, ('m9007', None, None, None, '')))

        # m11374 "KCL"
        self.assertEqual(parse_reference('/m0015#current'),
                (MODULE_REFERENCE, ('m0015', None, None, None, '#current')))

        # m11351 "electron and hole density equations"
        self.assertEqual(parse_reference('/m11332#ntypeq'),
                (MODULE_REFERENCE, ('m11332', None, None, None, '#ntypeq')))

        # m19809 "Gavin Bakers entry..."
        self.assertEqual(parse_reference('/ m19770'),
                (MODULE_REFERENCE, ('m19770', None, None, None, '')))

        # m16562 "Flat Stanley.pdf"
        self.assertEqual(parse_reference(' Flat Stanley.pdf'),
                (RESOURCE_REFERENCE, ('Flat Stanley.pdf', None, None)))

        # m34830 "Auto_fatalities_data.xls"
        self.assertEqual(parse_reference('/Auto_fatalities_data.xls'),
                (RESOURCE_REFERENCE, ('Auto_fatalities_data.xls', None, None)))

        # m35999 "version 2.3 of the first module"
        self.assertEqual(parse_reference('/m0000@2.3'),
                (MODULE_REFERENCE, ('m0000', '2.3', None, None, '')))

        # m14396 "Adding a Table..."
        # m11837
        # m37415
        # m37430
        # m10885
        self.assertEqual(parse_reference(
            '/content/m19610/latest/eip-edit-new-table.png'),
            (RESOURCE_REFERENCE, ('eip-edit-new-table.png', 'm19610', None)))

        # m45070
        self.assertEqual(parse_reference('/m'), (None, ()))

        # m45136 "legacy format"
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/latest?collection=col11441/latest'),
            (MODULE_REFERENCE, ('m48897', None, 'col11441', None, '')))
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/1.2?collection=col11441/1.10'),
            (MODULE_REFERENCE, ('m48897', '1.2', 'col11441', '1.10', '')))
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/1.2?collection=col11441/1.10'
            '#figure'),
            (MODULE_REFERENCE, ('m48897', '1.2', 'col11441', '1.10',
             '#figure')))

        # legacy.cnx.org links
        self.assertEqual(parse_reference(
            'http://legacy.cnx.org/content/m48897/latest'),
            (None, ()))
        self.assertEqual(parse_reference(
            'http://legacy.cnx.org/content/m48897/latest?collection=col11441/'
            'latest'), (None, ()))
