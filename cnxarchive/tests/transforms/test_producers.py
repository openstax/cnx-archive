# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import io
import unittest

from lxml import etree
from psycopg2 import Binary

from .. import testing


# ############### #
#   cnxml->html   #
# ############### #

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
        from ...transforms.producers import produce_html_for_abstract
        return produce_html_for_abstract(testing.fake_plpy,
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
        expected = 'href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce"'
        self.assertIn(expected, html)

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

        from ...transforms.producers import MissingAbstract
        with self.assertRaises(MissingAbstract) as caught_exception:
            self.call_target(document_ident)

    @testing.db_connect
    def test_abstract_w_resource_reference(self, cursor):
        # Case to ensure the reference resolution for resources.
        # This test requires a document_ident in order match with
        #   a module_files record.
        abstract = 'Image: <media><image mime-type="image/jpeg" src="Figure_01_00_01.jpg" /></media>'
        cursor.execute("INSERT INTO abstracts (abstract) VALUES (%s) "
                       "RETURNING abstractid", (abstract,))
        abstractid = cursor.fetchone()[0]

        # Create a minimal module entry to have a module_ident to work with.
        cursor.execute("""\
INSERT INTO modules
  (moduleid, portal_type, version, name, created, revised, authors,
   maintainers, licensors,  abstractid, stateid, licenseid, doctype,
   submitter, submitlog, language, parent)
VALUES
  ('m42119', 'Module', '1.1', 'New Version', '2013-09-13 15:10:43.000000+02' ,
   '2013-09-13 15:10:43.000000+02', NULL, NULL, NULL, %s, NULL, 11,
        '', NULL, '', 'en', NULL) RETURNING module_ident""", (abstractid,))
        document_ident = cursor.fetchone()[0]

        # Insert the resource file
        cursor.execute("""\
INSERT INTO module_files (module_ident, fileid, filename)
  SELECT %s, fileid, filename FROM module_files
  WHERE module_ident = 3 AND fileid = 6""", (document_ident,))

        # In the typical execution path, the target function
        #   would be using the same cursor, so there would be no
        #   reason to commit. But in this case, a new connection is made.
        cursor.connection.commit()
        self.call_target(document_ident)

        cursor.execute("select html from abstracts where abstractid = %s",
                       (abstractid,))
        html_abstract = cursor.fetchone()[0]
        self.assertIn(
            """Image: <span data-type="media"><img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" data-media-type="image/jpeg" alt=""/></span>""",
            html_abstract)


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
        from ...transforms.producers import produce_html_for_module
        return produce_html_for_module(testing.fake_plpy,
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

        from ...transforms.producers import MissingDocumentOrSource
        with self.assertRaises(MissingDocumentOrSource) as caught_exc:
            self.call_target(ident, filename)
        exception = caught_exc.exception

        self.assertEqual(exception.document_ident, ident)
        self.assertEqual(exception.filename, filename)

    def test_missing_document(self):
        # Case to test that we catch/raise exceptions when the document
        #   can't be found.
        ident, filename = 0, 'index.cnxml'

        from ...transforms.producers import MissingDocumentOrSource
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

        cursor.execute("SELECT fileid "
                       "FROM module_files "
                       "WHERE filename = 'index.cnxml.html' "
                       "AND module_ident != 2 LIMIT 1")
        fileid = cursor.fetchone()[0]
        cursor.execute("INSERT INTO module_files "
                       "(module_ident, fileid, filename) "
                       "VALUES (2, %s, 'index.cnxml.html')", (fileid,))
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

        cursor.execute("SELECT fileid "
                       "FROM module_files "
                       "WHERE filename = 'index.cnxml.html' "
                       "AND module_ident != 2 LIMIT 1")
        fileid = cursor.fetchone()[0]
        cursor.execute("INSERT INTO module_files "
                       "(module_ident, fileid, filename) "
                       "VALUES (2, %s, 'index.cnxml.html')", (fileid,))
        cursor.connection.commit()

        from ...transforms.producers import IndexFileExistsError

        with self.assertRaises(IndexFileExistsError) as e:
            self.call_target(2, overwrite_html=False)

        # Check the error message
        self.assertEqual(
            e.exception.message,
            "One of ('index.cnxml.html',) already exists for document 2")

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
        payload = (Binary(content), ident, filename,)
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


# ############### #
#   html->cnxml   #
# ############### #

class AbstractToCnxmlTestCase(unittest.TestCase):
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
        from ...transforms.producers import produce_cnxml_for_abstract
        return produce_cnxml_for_abstract(testing.fake_plpy,
                                          *args, **kwargs)

    @testing.db_connect
    def test_success(self, cursor):
        # Case to test for a successful tranformation of an abstract from
        #   html to cnxml.
        document_ident, abstractid = 2, 2  # m42955
        self.call_target(document_ident)

        cursor.execute("SELECT abstract FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        abstract = cursor.fetchone()[0]
        expected = 'A number list: <list list-type="bulleted"><item>one</item><item>two</item><item>three</item></list>'
        self.assertIn(expected, abstract)

    @testing.db_connect
    def test_success_w_reference(self, cursor):
        # Case with an abstract containing an internal reference.
        document_ident, abstractid = 3, 3
        self.call_target(document_ident)

        cursor.execute("SELECT abstract FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        abstract = cursor.fetchone()[0]
        expected = 'document="m42092"'
        self.assertIn(expected, abstract)

    @testing.db_connect
    def test_success_w_cnxml_root_element(self, cursor):
        # Case with an abstract that contains an outter xml element
        #   (e.g. <p>).
        document_ident, abstractid = 4, 4
        self.call_target(document_ident)

        cursor.execute("SELECT abstract FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        abstract = cursor.fetchone()[0]
        expected = '<para>A link to the <link url="http://example.com">outside world</link>.</para>'
        self.assertIn(expected, abstract)

    @testing.db_connect
    def test_success_w_no_cnxml(self, cursor):
        # Case that ensures plaintext abstracts remain unwrapped.
        document_ident, abstractid = 5, 5
        self.call_target(document_ident)

        cursor.execute("SELECT abstract FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        abstract = cursor.fetchone()[0]
        expected = 'A rather short plaintext abstract.'
        # Check for no tags.
        self.assertEqual(abstract, expected)

    @testing.db_connect
    def test_success_w_empty(self, cursor):
        # Case that ensures an empty abstract is saved as an empty html
        #   entry.
        document_ident, abstractid = 6, 6
        self.call_target(document_ident)

        cursor.execute("SELECT abstract FROM abstracts "
                       "  WHERE abstractid = %s;",
                       (abstractid,))
        abstract = cursor.fetchone()[0]
        self.assertEqual(abstract, '')

    def test_failure_on_nonexistent_document(self):
        # Case to ensure failure the requested document doesn't exist.
        document_ident, abstractid = 50, 50

        with self.assertRaises(ValueError) as caught_exception:
            self.call_target(document_ident)
        exception = caught_exception.exception
        # Just ensure that we aren't blind when the exception is raised.
        self.assertIn(str(document_ident), exception.message)

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

        from ...transforms.producers import MissingAbstract
        with self.assertRaises(MissingAbstract) as caught_exception:
            self.call_target(document_ident)


class ModuleToCnxmlTestCase(unittest.TestCase):
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
        from ...transforms.producers import produce_cnxml_for_module
        return produce_cnxml_for_module(testing.fake_plpy,
                                        *args, **kwargs)

    @testing.db_connect
    def test_html_source_missing(self, cursor):
        # Case to test that we catch/raise exceptions when the source
        #   file for a document can't be found.
        ident, filename = 2, 'index.cnxml.html'
        cursor.execute("DELETE FROM module_files "
                       "WHERE module_ident = %s AND filename = %s;",
                       (ident, filename,))
        cursor.connection.commit()

        from ...transforms.producers import MissingDocumentOrSource
        with self.assertRaises(MissingDocumentOrSource) as caught_exc:
            self.call_target(ident, filename)
        exception = caught_exc.exception

        self.assertEqual(exception.document_ident, ident)
        self.assertEqual(exception.filename, filename)

    def test_missing_document(self):
        # Case to test that we catch/raise exceptions when the document
        #   can't be found.
        ident, filename = 0, 'index.cnxml'

        from ...transforms.producers import MissingDocumentOrSource
        with self.assertRaises(MissingDocumentOrSource) as caught_exc:
            self.call_target(ident, filename)
        exception = caught_exc.exception

        self.assertEqual(exception.document_ident, ident)
        self.assertEqual(exception.filename, filename)

    @testing.db_connect
    def test_success(self, cursor):
        # Case to test for a successful tranformation of a module
        ident, filename = 2, 'index.cnxml.html'  # m42955

        # Delete module_ident 2 index.cnxml.html
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename LIKE %s", ('%.cnxml',))
        cursor.connection.commit()
        self.call_target(ident)

        cursor.execute("SELECT file FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = %s "
                       "         AND filename = 'index.html.cnxml');",
                       (ident,))
        index_cnxml = cursor.fetchone()[0][:]

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertIn('<document', index_cnxml)

    @testing.db_connect
    def test_module_transform_remove_index_cnxml(self, cursor):
        # Test when overwrite is True, the index.html.cnxml is removed
        # from the database before a new one is added

        # Delete module_ident 2 *.cnxml
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        cursor.execute("INSERT INTO module_files "
                       "(module_ident, fileid, filename) "
                       "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        cursor.connection.commit()

        msg = self.call_target(2, overwrite=True)

        # Assert there are no error messages
        self.assertEqual(msg, None)

        # Check cnxml is transformed to html
        cursor.execute("SELECT fileid, file FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = 2 "
                       "         AND filename = 'index.html.cnxml');")
        index_cnxml_id, index_cnxml = cursor.fetchone()
        index_cnxml = index_cnxml[:]

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertIn('<document', index_cnxml)

        # Assert index.cnxml.html has been replaced
        self.assertNotEqual(fileid, index_cnxml_id)

    @testing.db_connect
    def test_module_transform_index_html_cnxml_exists(self, cursor):
        # Test when overwrite is False, the index.html.cnxml
        # causes an error when a new one is generated

        # Create an index.html.cnxml for module_ident 2
        # Delete module_ident 2 index.html.cnxml
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        cursor.execute("INSERT INTO module_files "
                       "(module_ident, fileid, filename) "
                       "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        cursor.connection.commit()

        from ...transforms.producers import IndexFileExistsError

        with self.assertRaises(IndexFileExistsError) as e:
            self.call_target(2, overwrite=False)

        # Check the error message
        self.assertEqual(
            e.exception.message,
            "One of ('index.html.cnxml', 'index.cnxml') already exists for document 2")

        # Assert index.cnxml.html is not deleted
        cursor.execute("SELECT fileid FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = 2 "
                       "         AND filename = 'index.html.cnxml');")
        index_cnxml_id = cursor.fetchone()[0]

        self.assertEqual(fileid, index_cnxml_id)

    @testing.db_connect
    def test_module_transform_index_cnxml_exists(self, cursor):
        # Test when overwrite is False, the index.html.cnxml
        # causes an error when a new one is generated

        # Create an index.html.cnxml for module_ident 2
        # Delete module_ident 2 index.cnxml
        cursor.execute("DELETE FROM module_files WHERE module_ident = 2 "
                       "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        cursor.execute("INSERT INTO module_files "
                       "(module_ident, fileid, filename) "
                       "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        cursor.connection.commit()

        from ...transforms.producers import IndexFileExistsError

        with self.assertRaises(IndexFileExistsError) as e:
            self.call_target(2, overwrite=False)

        # Check the error message
        self.assertEqual(
            e.exception.message,
            "One of ('index.html.cnxml', 'index.cnxml') already exists for document 2")

        # Assert index.cnxml.html is not deleted
        cursor.execute("SELECT fileid FROM files "
                       "  WHERE fileid = "
                       "    (SELECT fileid FROM module_files "
                       "       WHERE module_ident = 2 "
                       "         AND filename = 'index.html.cnxml');")
        index_cnxml_id = cursor.fetchone()[0]

        self.assertEqual(fileid, index_cnxml_id)

    @testing.db_connect
    def _make_document_data_invalid(self, cursor, ident, filename):
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
        file = cursor.fetchone()[0][:]
        # Make a mess of things...
        content = file[:600] + file[700:]
        payload = (Binary(content), ident, filename,)
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
        ident = self._make_document_data_invalid(2, 'index.cnxml.html')

        # Delete ident *.cnxml
        cursor.execute('DELETE FROM module_files WHERE '
                       'module_ident = %s AND filename LIKE %s',
                       [ident, '%.cnxml'])
        cursor.connection.commit()

        with self.assertRaises(Exception) as caught_exc:
            self.call_target(ident)

        exception = caught_exc.exception
        from lxml.etree import XMLSyntaxError
        self.assertTrue(isinstance(exception, XMLSyntaxError))
        self.assertIn(
            u"attributes construct error, line 2",
            exception.message)
