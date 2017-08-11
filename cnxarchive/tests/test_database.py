# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import datetime
import hashlib
import json
import os
import sys
import time
import unittest

from cnxepub import flatten_tree_to_ident_hashes
import psycopg2

from . import testing


class MiscellaneousFunctionsTestCase(unittest.TestCase):
    fixture = testing.schema_fixture

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def test_iso8601(self, cursor):
        # Exams the iso8601 SQL function.
        cursor.execute("SELECT date_trunc('second', current_timestamp), iso8601(current_timestamp);")
        current, iso8601 = cursor.fetchone()
        # We need to make the date timezone aware, which is what the 'Z' does,
        #   but the parsing statement can't do anything with that.
        # We'll use psycopg2's tzinfo classes for simplicity.
        from psycopg2.tz import FixedOffsetTimezone
        value = datetime.datetime(*time.strptime(iso8601,
                                  "%Y-%m-%dT%H:%M:%SZ")[:6], tzinfo=FixedOffsetTimezone())
        self.assertEqual(current, value)

    @unittest.skipIf(not testing.is_venv(),
                     "Not within a virtualenv")
    @testing.db_connect
    def test_pypath(self, cursor):
        site_packages = testing.getsitepackages()
        # Examine the results of the pypath SQL function.
        cursor.execute("SELECT unnest(pypath())")
        paths = [row[0] for row in cursor.fetchall()]

        for site_pkg in site_packages:
            self.assertIn(os.path.abspath(site_pkg), paths)

    @testing.db_connect
    def test_pyimport(self, cursor):
        target_name = 'cnxarchive.database'

        # Import the module from current directory
        import cnxarchive.database as target_source

        # Remove current directory from sys.path
        cwd = os.getcwd()
        sys_path = sys.path
        modified_path = [i for i in sys_path if i and i != cwd]
        sys.path = modified_path
        self.addCleanup(setattr, sys, 'path', sys_path)

        # Depending on whether "setup.py develop" or "setup.py install" is
        # used, there are different expected directories and file paths.
        targets = [target_source]

        # This is basically what pip does to determine whether a file
        # is editable or installed.
        import pkg_resources
        dist = pkg_resources.get_distribution('cnx-archive')
        is_editable = False
        for path_item in sys.path:
            egg_link = os.path.join(path_item, dist.project_name + '.egg-link')
            if os.path.isfile(egg_link):
                # it's an editable install rather than a fixed install.
                is_editable = True
                break

        if not is_editable:
            # Remove all cnxarchive modules from sys.modules
            sys_modules = sys.modules.copy()
            self.addCleanup(sys.modules.update, sys_modules)
            for module in sys.modules.keys():
                if module.startswith('cnxarchive'):
                    del sys.modules[module]

            # Import the installed version, if "setup.py install" was used.
            import cnxarchive.database as target_installed
            targets.append(target_installed)

        expected_directories = [
            os.path.abspath(os.path.dirname(target.__file__))
            for target in targets]
        expected_file_paths = [
            target.__file__ for target in targets]

        # Check the results of calling pyimport on cnxarchive.
        cursor.execute("SELECT import, directory, file_path "
                       "FROM pyimport(%s)", (target_name,))
        import_, directory, file_path = cursor.fetchone()

        self.assertEqual(import_, target_name)
        self.assertIn(directory, expected_directories)
        self.assertIn(file_path, expected_file_paths)

    @testing.db_connect
    def test_pyimport_with_importerror(self, cursor):
        target_name = 'hubris'
        # Check the results of calling pyimport on cnxarchive.
        cursor.execute("SELECT import, directory, file_path "
                       "FROM pyimport(%s)", (target_name,))
        row = cursor.fetchone()

        self.assertEqual(row, None)

    @testing.db_connect
    def test_module_ident_from_ident_hash(self, cursor):
        uuid = 'c395b566-5fe3-4428-bcb2-19016e3aa3ce'
        module_ident = 10
        # Create a piece of content.
        cursor.execute("INSERT INTO document_controls (uuid) VALUES (%s)",
                       (uuid,))
        cursor.execute("""\
        INSERT INTO modules
          (module_ident, portal_type, uuid, name, licenseid, doctype)
        VALUES
          (%s, 'Module', %s, 'Physics: An Introduction', 11, '')""",
                       (module_ident, uuid,))

        from ..database import get_module_ident_from_ident_hash
        self.assertEqual(get_module_ident_from_ident_hash(uuid[:-1]+'c', cursor), None)
        self.assertEqual(get_module_ident_from_ident_hash(uuid, cursor), module_ident)
        self.assertEqual(get_module_ident_from_ident_hash(uuid+"@1", cursor), module_ident)

        # Add a minor_version to the content.
        for table_name in ('modules', 'latest_modules',):
            cursor.execute("""\
            UPDATE {} SET (minor_version) = (3)
            WHERE module_ident = %s""".format(table_name),
                           (module_ident,))
        self.assertEqual(get_module_ident_from_ident_hash(uuid+"@1", cursor), module_ident)
        self.assertEqual(get_module_ident_from_ident_hash(uuid+"@1.3", cursor), module_ident)

    @testing.db_connect
    def test_html_abstract_deprecated(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (3, 'A link to an <link document="m42092">interal document</link>.', '');
        ''')
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, '<para>A link to the <link url="http://example.com">outside world</link>.</para>', '');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', DEFAULT, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        # set the html abstract using the html_abstract function
        cursor.execute('UPDATE abstracts SET html = html_abstract(abstract) RETURNING html;')

        # check that the abstracts have been transformed
        html_abstract3 = cursor.fetchone()[0]
        html_abstract3 = html_abstract3[html_abstract3.index('>') + 1:]  # strip the div tag
        self.assertEqual(html_abstract3,
                         'A link to an <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce">interal document</a>.</div>')
        html_abstract4 = cursor.fetchone()[0]
        html_abstract4 = html_abstract4[html_abstract4.index('>') + 1:]  # strip the div tag
        self.assertTrue(html_abstract4,
                        'A link to the <a href="http://example.com">outside world</a>.</div>')

    @testing.db_connect
    def test_html_abstract(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, 'A link to an <link document="m42092">interal document</link>.', '');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', DEFAULT, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        # set the html abstract using the html_abstract function
        cursor.execute('UPDATE abstracts SET html = html_abstract(4) RETURNING html;')

        # check that the abstracts have been transformed
        html_abstract = cursor.fetchone()[0]
        html_abstract = html_abstract[html_abstract.index('>') + 1:]  # strip the div tag
        self.assertEqual(html_abstract,
                         'A link to an <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce">interal document</a>.</div>')

    @testing.db_connect
    def test_cnxml_abstract(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, '', '<div xmlns="http://www.w3.org/1999/xhtml">A link to an <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce">interal document</a>.</div>');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', DEFAULT, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        # set the html abstract using the html_abstract function
        cursor.execute('UPDATE abstracts SET abstract = cnxml_abstract(4) RETURNING abstract;')

        # check that the abstracts have been transformed
        cnxml_abstract = cursor.fetchone()[0]
        self.assertEqual(cnxml_abstract,
                         'A link to an <link document="m42092" version="1.4">interal document</link>.')

    @testing.db_connect
    def test_html_content_deprecated(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, '<para>A link to the <link url="http://example.com">outside world</link>.</para>', '');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        cursor.execute('SELECT fileid FROM files')

        cnxml_filepath = os.path.join(testing.DATA_DIRECTORY,
                                      'm42033-1.3.cnxml')
        with open(cnxml_filepath, 'r') as f:
            cursor.execute('''\
            INSERT INTO files (file, media_type) VALUES
            (%s, 'text/xml') RETURNING fileid''', [memoryview(f.read())])
            fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename) VALUES
        (4, %s, 'index.cnxml');''', [fileid])

        # check that cnxml content can be transformed
        cursor.execute('''\
        SELECT html_content(encode(file, 'escape')::text)
        FROM files''')
        content = cursor.fetchone()[0]
        # Only test for general conversion.
        self.assertIn('<body', content)

    @testing.db_connect
    def test_html_content(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, '<para>A link to the <link url="http://example.com">outside world</link>.</para>', '');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        cursor.execute('SELECT fileid FROM files')

        cnxml_filepath = os.path.join(testing.DATA_DIRECTORY,
                                      'm42033-1.3.cnxml')
        with open(cnxml_filepath, 'r') as f:
            cursor.execute('''\
            INSERT INTO files (file, media_type) VALUES
            (%s, 'text/xml') RETURNING fileid''', [memoryview(f.read())])
            fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename) VALUES
        (4, %s, 'index.cnxml');''', [fileid])

        # check that cnxml content can be transformed
        html_filepath = os.path.join(testing.DATA_DIRECTORY,
                                     'm42033-1.3.html')
        with open(html_filepath, 'r') as f:
            html_content = f.read()
        cursor.execute("SELECT html_content(4) FROM files")
        self.assertIn("<body", cursor.fetchone()[0])

    @testing.db_connect
    def test_cnxml_content(self, cursor):
        # insert test data
        cursor.execute('''\
        INSERT INTO abstracts VALUES
        (4, '<para>A link to the <link url="http://example.com">outside world</link>.</para>', '');
        ''')
        cursor.execute("""\
        INSERT INTO document_controls (uuid) VALUES ('d395b566-5fe3-4428-bcb2-19016e3aa3ce');""")
        cursor.execute('''\
        INSERT INTO modules VALUES
        (4, 'Module', 'm42092', 'd395b566-5fe3-4428-bcb2-19016e3aa3ce', '1.4',
        'Physics: An Introduction', '2013-07-31 14:07:20.75499-05', '2013-07-31
        14:07:20.75499-05', 4, 11, '', '46cf263d-2eef-42f1-8523-1b650006868a',
        '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}',
        '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8,1df3bab1-1dc7-4017-9b3a-960a87e706b1}',
        '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 4, NULL);''')
        cursor.execute('SELECT fileid FROM files')

        filepath = os.path.join(testing.DATA_DIRECTORY, 'm42033-1.3.html')
        with open(filepath, 'r') as f:
            cursor.execute('''\
            INSERT INTO files (file, media_type) VALUES
            (%s, 'text/xml') RETURNING fileid''', [memoryview(f.read())])
            fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename) VALUES
        (4, %s, 'index.cnxml.html');''', [fileid])

        # check that cnxml content can be transformed
        filepath = os.path.join(testing.DATA_DIRECTORY,
                                'm42033-1.3.cnxml')
        with open(filepath, 'r') as f:
            cnxml_content = f.read()
        cursor.execute("SELECT cnxml_content(4) FROM files")
        self.assertIn("<document", cursor.fetchone()[0])

    @testing.db_connect
    def test_identifiers_equal_function(self, cursor):
        import inspect

        from .test_utils import identifiers_equal

        cursor.execute("""\
CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 text, identifier2 text)
  RETURNS BOOLEAN
AS $$
import uuid
from cnxarchive.utils import CNXHash, IdentHashSyntaxError

{}

return identifiers_equal(identifier1, identifier2)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 uuid, identifier2 uuid)
  RETURNS BOOLEAN
AS $$
  SELECT identifiers_equal(identifier1::text, identifier2::text)
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 text, identifier2 uuid)
  RETURNS BOOLEAN
AS $$
  SELECT identifiers_equal(identifier1, identifier2::text)
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 uuid, identifier2 text)
  RETURNS BOOLEAN
AS $$
  SELECT identifiers_equal(identifier1::text, identifier2)
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION uuid2base64 (identifier uuid)
  RETURNS character(24)
AS $$
  from cnxarchive.utils import CNXHash
  return CNXHash.uuid2base64(identifier)
$$ LANGUAGE plpythonu;
""".format(inspect.getsource(identifiers_equal)))

        import uuid
        cursor.execute(
            "select identifiers_equal(uuid_generate_v4(),uuid_generate_v4())")
        self.assertFalse(cursor.fetchone()[0])

        cursor.execute(
            "select identifiers_equal(uuid_generate_v4(), uuid2base64(uuid_generate_v4()))")
        self.assertFalse(cursor.fetchone()[0])

        cursor.execute(
            "select identifiers_equal(uuid2base64(uuid_generate_v4()),uuid_generate_v4())")
        self.assertFalse(cursor.fetchone()[0])

        cursor.execute(
            "select identifiers_equal(uuid2base64(uuid_generate_v4()), uuid2base64(uuid_generate_v4()))")
        self.assertFalse(cursor.fetchone()[0])

        identifier = str(uuid.uuid4())

        cursor.execute(
            "select identifiers_equal('{}','{}')".format(identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal('{}'::uuid,'{}'::uuid)".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute(
            "select identifiers_equal('{}','{}'::uuid)".format(identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute(
            "select identifiers_equal('{}'::uuid,'{}')".format(identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal('{}', uuid2base64('{}'))".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal('{}'::uuid, uuid2base64('{}'))".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal(uuid2base64('{}'),'{}')".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal(uuid2base64('{}'),'{}'::uuid)".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

        cursor.execute("select identifiers_equal(uuid2base64('{}'), uuid2base64('{}'))".format(
            identifier, identifier))
        self.assertTrue(cursor.fetchone()[0])

    @testing.db_connect
    def test_strip_html(self, cursor):
        cursor.execute("SELECT strip_html('no html')")
        result = cursor.fetchone()[0]
        self.assertEqual('no html', result)

        cursor.execute("""\
SELECT strip_html('<span><span class="number">1.1</span> \
<span class="divider"> | </span>\
<span class="text">Sampling Experiment</span></span>')""")
        result = cursor.fetchone()[0]
        self.assertEqual('1.1  | Sampling Experiment', result)

        cursor.execute("SELECT strip_html('<span>三百年</span>')")
        result = cursor.fetchone()[0]
        self.assertEqual('三百年', result)

        cursor.execute("""\
SELECT strip_html('<span
 class="number">1.1</span> multi-
line')""")
        result = cursor.fetchone()[0]
        self.assertEqual('1.1 multi-\nline', result)


class TreeToJsonTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.fixture.setUp()
        cls._insert_collated_tree()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDown()

    @classmethod
    def _insert_collated_tree(cls):
        connect = testing.db_connection_factory()
        nodes = [
            # nodeid, parent_id, documentid, title, childorder
            (936, None, 1, None, 0,),
            (937, 936, 2, 'Preface', 2,),
            (938, 936, None, 'Introduction: The Nature of Science and Physics', 3,),
            (944, 936, None, "Further Applications of Newton's Laws: Friction, Drag, and Elasticity", 4,),
            (949, 936, 12, None, 5,),
            (950, 936, 13, None, 6,),
            (951, 936, 14, None, 7,),
            (952, 936, 15, None, 8,),
            # subcol of 938, clone of nodeid=38
            (939, 938, 3, None, 2,),
            (940, 938, 4, None, 3,),
            (941, 938, 5, None, 4,),
            (942, 938, 6, None, 5,),
            (943, 938, 7, None, 6,),
            # subcol of 944, clone of nodeid=44
            (945, 944, 8, None, 2,),
            (946, 944, 9, None, 3,),
            (947, 944, 10, None, 4,),
            (948, 944, 11, None, 5,),
            # collated bits that have been added...
            (991, 936, None, "Collated Added Sub-collection", 9,),
            # (992, 991, ???, None, 2,),  # where m.portal_type='CompositeModule'
            ]

        def insert_tree_node(cursor, entry):
            cursor.execute("INSERT INTO trees"
                           "  (nodeid, parent_id, documentid, title, childorder,"
                           "   latest, is_collated) "
                           "VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)", entry)

        # Useful if you need to make changes...
        # This will help you check the clone is valid (identity check).
        # ident_hash = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        # version = '7.1'
        # with connect() as db_conn:
        #    with db_conn.cursor() as cursor:
        #        for node_entry in nodes[:17]:
        #            insert_tree_node(cursor, node_entry)
        #        cursor.execute("SELECT tree_to_json(%(i)s, %(v)s), tree_to_json(%(i)s, %(v)s, FALSE)",
        #                       dict(i=ident_hash, v=version))
        #        orig_tree, collated_tree = cursor.fetchone()
        #        try:
        #            assert orig_tree == collated_tree
        #        except AssertionError:
        #            print(orig_tree)
        #            print('+'*10)
        #            print(collated_tree)
        #            raise
        #        else:
        #            cursor.execute("DELETE FROM trees WHERE nodeid >= 900")

        with connect() as db_conn:
            with db_conn.cursor() as cursor:
                for node_entry in nodes:
                    insert_tree_node(cursor, node_entry)

    @property
    def target(self):
        connect = testing.db_connection_factory()

        def get_tree(consume_raw=False):
            args = ['e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1']
            stmt = "select tree_to_json(%s, %s)"
            if consume_raw:
                stmt = "select tree_to_json(%s, %s, FALSE)"
            with connect() as db_connection:
                with db_connection.cursor() as cursor:
                    cursor.execute(stmt, args)
                    tree = cursor.fetchone()[0]
            return json.loads(tree)

        return get_tree

    def test_get_tree(self):
        tree = self.target()
        # Check for the collated tree values.
        self.assertEqual(
            tree['contents'][-1]['title'],
            "Collated Added Sub-collection")

    def test_get_raw_tree(self):
        tree = self.target(consume_raw=True)
        # Check for the *absence* of the collated tree values.
        self.assertNotEqual(
            tree['contents'][-1]['title'],
            "Collated Added Sub-collection")


SQL_FOR_HIT_DOCUMENTS = """
ALTER TABLE modules DISABLE TRIGGER ALL;
INSERT INTO abstracts VALUES (1, '');
INSERT INTO modules VALUES (
  1, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.1', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  2, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.2', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 2, NULL);
INSERT INTO modules VALUES (
  3, 'Module', 'm2', 'f122af91-5f4f-4736-a502-67bd0a1628aa',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  4, 'Module', 'm3', 'c8ee8dc5-bb73-47c8-b10f-3f37123cf607',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO modules VALUES (
  5, 'Module', 'm4', 'dd7b92c2-e82e-43bb-b224-accbc3cd395a',
  '1.1', 'Name of m4',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO modules VALUES (
  6, 'Module', 'm5', '84b98813-928b-4f3f-b7d0-0472c82bfd1c',
  '1.1', 'Name of m5',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 2;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 3;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 4;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 5;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 6;
ALTER TABLE modules ENABLE TRIGGER ALL;
"""


class DocumentHitsTestCase(unittest.TestCase):
    fixture = testing.schema_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        cursor.execute(SQL_FOR_HIT_DOCUMENTS)

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def override_recent_date(self, cursor):
        # Override the SQL function for acquiring the recent date,
        #   because otherwise the test will be a moving target in time.
        cursor.execute("CREATE OR REPLACE FUNCTION get_recency_date () "
                       "RETURNS TIMESTAMP AS $$ BEGIN "
                       "  RETURN '2013-10-20'::timestamp with time zone; "
                       "END; $$ LANGUAGE plpgsql;")

    @testing.db_connect
    def make_hit(self, cursor, ident, start_date, end_date=None, count=0):
        from datetime import timedelta
        if end_date is None:
            end_date = start_date + timedelta(1)
        payload = (ident, start_date, end_date, count,)
        cursor.execute("INSERT INTO document_hits "
                       "  VALUES (%s, %s, %s, %s);",
                       payload)

    def create_hits(self):
        from datetime import datetime, timedelta
        recent_date = datetime(2013, 10, 20)
        dates = (recent_date - timedelta(2),
                 recent_date - timedelta(1),
                 recent_date,
                 recent_date + timedelta(1),
                 recent_date + timedelta(2),
                 )
        hits = {
            # module_ident: [hits]    # total, recent
            1: [1, 1, 9, 7, 15],      # 33, 31
            2: [9, 2, 5, 7, 11],      # 34, 23
            # combined 1 & 2          #
            3: [1, 2, 3, 4, 1],       # 11, 8
            4: [3, 3, 3, 3, 3],       # 15, 9
            5: [7, 9, 11, 7, 5],      # 39, 23
            6: [18, 20, 13, 12, 24],  # 87, 49
            }
        for i, date in enumerate(dates):
            for ident, hit_counts in hits.items():
                self.make_hit(ident, date, count=hit_counts[i])
        return hits

    @testing.db_connect
    def test_recency_function_w_no_document_hits(self, cursor):
        # Exam the function out puts a date.

        # At the time of this writting the recency is one week.
        from datetime import datetime, timedelta
        then = datetime.today() - timedelta(7)

        cursor.execute("SELECT get_recency_date();")
        value = cursor.fetchone()[0]
        # We're mostly checking by the day rather than by time,
        #   so checking by date should be sufficient.
        self.assertEqual(then.date(), value.date())

    @testing.db_connect
    def test_recency_function_w_document_hits(self, cursor):
        # Exam the function out puts a date.

        self.create_hits()
        cursor.execute('SELECT MAX(end_timestamp) FROM document_hits')
        max_end_timestamp = cursor.fetchone()[0]

        # At the time of this writting the recency is one week.
        from datetime import datetime, timedelta
        then = max_end_timestamp - timedelta(7)

        cursor.execute("SELECT get_recency_date();")
        value = cursor.fetchone()[0]
        # We're mostly checking by the day rather than by time,
        #   so checking by date should be sufficient.
        self.assertEqual(then.date(), value.date())

    @testing.db_connect
    def test_hit_average_function(self, cursor):
        # Verify the hit average is output in both overall and recent
        #   circumstances.
        self.override_recent_date()
        hits = self.create_hits()

        cursor.execute("SELECT hit_average(1, NULL);")
        average = cursor.fetchone()[0]
        cursor.execute("SELECT hit_average(1, 't');")
        recent_average = cursor.fetchone()[0]
        cursor.execute("SELECT hit_average(6, 'f');")
        other_average = cursor.fetchone()[0]

        self.assertEqual(average, sum(hits[1]) / 5.0)
        from math import ceil

        def close_enough(d):
            return ceil(d * 1000) / 1000
        self.assertEqual(close_enough(recent_average),
                         close_enough(sum(hits[1][2:]) / 3.0))
        self.assertEqual(close_enough(other_average),
                         close_enough(sum(hits[6]) / 5.0))

    @testing.db_connect
    def test_hit_rank_function(self, cursor):
        # Verify the hit rank is output in both overall and recent
        #   circumstances.
        self.override_recent_date()
        hits = self.create_hits()

        cursor.execute("SELECT hit_rank(5, 'f');")
        rank = cursor.fetchone()[0]
        cursor.execute("SELECT hit_rank(5, 't');")
        recent_rank = cursor.fetchone()[0]

        self.assertEqual(rank, 5)
        self.assertEqual(recent_rank, 3)

    @testing.db_connect
    def test_update_recent_hits_function(self, cursor):
        # Verify the function updates the recent hit ranks table
        #   with hit rank information grouped by document uuid.
        self.override_recent_date()
        hits = self.create_hits()

        # Call the target SQL function.
        cursor.execute("SELECT update_hit_ranks();")
        cursor.execute("SELECT * FROM recent_hit_ranks "
                       "ORDER BY rank ASC;")
        hit_ranks = cursor.fetchall()

        self.assertEqual(hit_ranks[1],
                         ('c8ee8dc5-bb73-47c8-b10f-3f37123cf607', 9, 3, 2))
        self.assertEqual(hit_ranks[3],  # row that combines two idents.
                         ('88cd206d-66d2-48f9-86bb-75d5366582ee', 54, 9, 4))

    @testing.db_connect
    def test_update_overall_hits_function(self, cursor):
        # Verify the function updates the overall hit ranks table
        #   with hit rank information grouped by document uuid.
        self.override_recent_date()
        hits = self.create_hits()

        # Call the target SQL function.
        cursor.execute("SELECT update_hit_ranks();")
        cursor.execute("SELECT * FROM overall_hit_ranks "
                       "ORDER BY rank ASC;")
        hit_ranks = cursor.fetchall()

        self.assertEqual(hit_ranks[2],  # row that combines two idents.
                         ('88cd206d-66d2-48f9-86bb-75d5366582ee', 67, 6.7, 3))
        # Note, this module has fewer hits in total, but more on average,
        #   which expectedly boosts its rank.
        self.assertEqual(hit_ranks[3],
                         ('dd7b92c2-e82e-43bb-b224-accbc3cd395a', 39, 7.8, 4))
