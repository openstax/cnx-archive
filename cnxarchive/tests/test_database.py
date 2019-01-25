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
import re
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

    @unittest.skipIf(not testing.db_is_local(),
                     'Database is not on the same host')
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


class ModulePublishTriggerTestCase(unittest.TestCase):
    """Tests for the postgresql triggers when a module is published
    """
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def test_get_current_module_ident(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from ..database import get_current_module_ident

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, 1)''')

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, 1) RETURNING module_ident''')

        expected_module_ident = cursor.fetchone()[0]
        cursor.connection.commit()
        module_ident = get_current_module_ident('m1', testing.fake_plpy)

        self.assertEqual(module_ident, expected_module_ident)

    @testing.db_connect
    def test_next_version(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER collection_minor_ver_collxml')
        from ..database import next_version

        # Insert collection version 2.1
        cursor.execute('''INSERT INTO modules
        (moduleid, portal_type, version, name,
        created, revised,
        authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent,
        major_version, minor_version)
        VALUES (
        'c1', 'Collection', '1.2', 'Name of c1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        '{}', '{}', '{}', 1, 1, 7, '', '', '', 'en', NULL,
        2, 1) RETURNING module_ident''')
        module_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        # The next version should be 2.2
        self.assertEqual(next_version(module_ident, testing.fake_plpy), 2)

        # Insert collection version 2.2
        cursor.execute('''INSERT INTO modules
        (moduleid, portal_type, version, name,
        created, revised,
        authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent,
        major_version, minor_version)
        VALUES (
        'c1', 'Collection', '1.2', 'Name of c1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        '{}', '{}', '{}', 1, 1, 7, '', '', '', 'en', NULL,
        2, 2)''')
        cursor.connection.commit()

        # Even if you use the module_ident for version 2.1, the next version is
        # still going to be 2.3
        self.assertEqual(next_version(module_ident, testing.fake_plpy), 3)

    @testing.db_connect
    def test_get_collections(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from ..database import get_collections

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', DEFAULT, '1.9', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 9, 1) RETURNING module_ident''')
        collection_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col2', DEFAULT, '1.8', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 8, 1) RETURNING module_ident''')
        collection2_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, 1) RETURNING module_ident''')
        module_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, NULL, %s, 'title', 0, NULL) RETURNING nodeid''',
                       [collection_ident])
        nodeid = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, %s, %s, 'title', 1, NULL)''', [nodeid, module_ident])

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, NULL, %s, 'title', 0, NULL) RETURNING nodeid''',
                       [collection2_ident])
        nodeid = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, %s, %s, 'title', 1, NULL)''', [nodeid, module_ident])

        cursor.connection.commit()

        self.assertEqual(
            list(get_collections(module_ident, testing.fake_plpy)),
            [collection_ident, collection2_ident])

    @testing.db_connect
    def test_rebuild_collection_tree(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from ..database import rebuild_collection_tree

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', DEFAULT, '1.9', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 9, 1) RETURNING module_ident''')
        collection_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, 1) RETURNING module_ident''')
        module_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm2', DEFAULT, '1.1', 'Name of m2',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, 1) RETURNING module_ident''')
        module2_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, NULL, %s, 'title', 0, NULL) RETURNING nodeid''',
                       [collection_ident])
        nodeid = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, %s, %s, 'title', 1, NULL)''', [nodeid, module_ident])

        cursor.execute('''INSERT INTO trees VALUES (
        DEFAULT, %s, %s, 'title', 1, NULL)''', [nodeid, module2_ident])

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', DEFAULT, '1.9', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 10, 1) RETURNING module_ident''')
        new_collection_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 3, 1) RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        new_document_id_map = {
            collection_ident: new_collection_ident,
            module_ident: new_module_ident
            }
        rebuild_collection_tree(collection_ident, new_document_id_map,
                                testing.fake_plpy)

        cursor.execute('''\
        WITH RECURSIVE t(node, parent, document, path) AS (
            SELECT tr.nodeid, tr.parent_id, tr.documentid, ARRAY[tr.nodeid]
            FROM trees tr WHERE tr.documentid = %s
        UNION ALL
            SELECT c.nodeid, c.parent_id, c.documentid, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON (t.node = c.parent_id)
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT document FROM t
        ''', [new_collection_ident])
        self.assertEqual(cursor.fetchall(), [[new_collection_ident],
                         [new_module_ident], [module2_ident]])

    @testing.db_connect
    def test_republish_collection(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER collection_minor_ver_collxml')

        from ..database import republish_collection

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', '3a5344bd-410d-4553-a951-87bccd996822',
        '1.10', 'Name of c1', '2013-07-31 12:00:00.000000-07',
        '2013-10-03 21:59:12.000000-07', 1, 11, 'doctype', 'submitter',
        'submitlog', NULL, NULL, 'en', '{authors}', '{maintainers}',
        '{licensors}', '{parentauthors}', 'analytics code', 'buylink', 10, 1
        ) RETURNING module_ident''')
        collection_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        republished_submitter = "republished_submitter"
        republished_submitlog = "republished_submitlog"

        new_ident = republish_collection(republished_submitter,
                                         republished_submitlog, 3,
                                         collection_ident, testing.fake_plpy)

        cursor.execute('''SELECT * FROM modules WHERE
        module_ident = %s''', [new_ident])
        data = cursor.fetchone()
        self.assertEqual(data[1], 'Collection')
        self.assertEqual(data[2], 'col1')
        self.assertEqual(data[3], '3a5344bd-410d-4553-a951-87bccd996822')
        self.assertEqual(data[4], '1.10')
        self.assertEqual(data[5], 'Name of c1')
        self.assertEqual(str(data[6]), '2013-07-31 12:00:00-07:00')
        self.assertNotEqual(str(data[7]), '2013-10-03 21:59:12-07:00')
        self.assertEqual(data[8], 1)
        self.assertEqual(data[9], 11)
        self.assertEqual(data[10], 'doctype')
        self.assertEqual(data[11], republished_submitter)
        self.assertEqual(data[12], republished_submitlog)
        self.assertEqual(data[13], 5)
        self.assertEqual(data[14], None)
        self.assertEqual(data[15], 'en')
        self.assertEqual(data[16], ['authors'])
        self.assertEqual(data[17], ['maintainers'])
        self.assertEqual(data[18], ['licensors'])
        self.assertEqual(data[19], ['parentauthors'])
        self.assertEqual(data[20], 'analytics code')
        self.assertEqual(data[21], 'buylink')
        self.assertEqual(data[22], 10)
        self.assertEqual(data[23], 3)

    @testing.db_connect
    def test_republish_collection_w_keywords(self, cursor):
        # Ensure association of the new collection with existing keywords.
        settings = testing.integration_test_settings()
        cursor.execute("ALTER TABLE modules DISABLE TRIGGER module_published")
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER collection_minor_ver_collxml')

        cursor.connection.commit()

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', '3a5344bd-410d-4553-a951-87bccd996822',
        '1.10', 'Name of c1', '2013-07-31 12:00:00.000000-07',
        '2013-10-03 21:59:12.000000-07', 1, 11, 'doctype', 'submitter',
        'submitlog', NULL, NULL, 'en', '{authors}', '{maintainers}',
        '{licensors}', '{parentauthors}', 'analytics code', 'buylink', 10, 1
        ) RETURNING module_ident;''')
        collection_ident = cursor.fetchone()[0]
        keywords = ['smoo', 'dude', 'gnarly', 'felice']
        values_expr = ", ".join("('{}')".format(v) for v in keywords)
        cursor.execute("""INSERT INTO keywords (word)
        VALUES {}
        RETURNING keywordid;""".format(values_expr))
        keywordids = [x[0] for x in cursor.fetchall()]
        values_expr = ", ".join(["({}, '{}')".format(collection_ident, id)
                                 for id in keywordids])
        cursor.execute("""INSERT INTO modulekeywords (module_ident, keywordid)
        VALUES {};""".format(values_expr))
        cursor.connection.commit()

        from ..database import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT",
                                         3, collection_ident,
                                         testing.fake_plpy)

        cursor.execute("""\
        SELECT word
        FROM modulekeywords NATURAL JOIN keywords
        WHERE module_ident = %s""", (new_ident,))

        inserted_keywords = [x[0] for x in cursor.fetchall()]
        self.assertEqual(sorted(inserted_keywords), sorted(keywords))

    @testing.db_connect
    def test_republish_collection_w_files(self, cursor):
        # Ensure association of the new collection with existing files.
        settings = testing.integration_test_settings()
        cursor.execute("""\
ALTER TABLE modules DISABLE TRIGGER module_published""")
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER collection_minor_ver_collxml')

        cursor.connection.commit()

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', '3a5344bd-410d-4553-a951-87bccd996822',
        '1.10', 'Name of c1', '2013-07-31 12:00:00.000000-07',
        '2013-10-03 21:59:12.000000-07', 1, 11, 'doctype', 'submitter',
        'submitlog', NULL, NULL, 'en', '{authors}', '{maintainers}',
        '{licensors}', '{parentauthors}', 'analytics code', 'buylink', 10, 1
        ) RETURNING module_ident;''')
        collection_ident = cursor.fetchone()[0]

        filepath = os.path.join(testing.DATA_DIRECTORY, 'ruleset.css')
        with open(filepath, 'r') as f:
            cursor.execute('''\
            INSERT INTO files (file, media_type) VALUES
            (%s, 'text/css') RETURNING fileid''', [memoryview(f.read())])
            fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename) VALUES
        (%s, %s, 'ruleset.css');''', [collection_ident, fileid])

        cursor.connection.commit()

        from ..database import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT",
                                         3, collection_ident,
                                         testing.fake_plpy)

        cursor.execute("""\
        SELECT fileid, filename
        FROM module_files
        WHERE module_ident = %s""", (new_ident,))

        inserted_files = cursor.fetchall()
        self.assertEqual(sorted(inserted_files),
                         sorted([[fileid, 'ruleset.css']]))

    @testing.db_connect
    def test_republish_collection_w_subjects(self, cursor):
        # Ensure association of the new collection with existing subjects/tags.
        settings = testing.integration_test_settings()
        cursor.execute("""\
ALTER TABLE modules DISABLE TRIGGER module_published""")
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER collection_minor_ver_collxml')

        cursor.connection.commit()

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'col1', '3a5344bd-410d-4553-a951-87bccd996822',
        '1.10', 'Name of c1', '2013-07-31 12:00:00.000000-07',
        '2013-10-03 21:59:12.000000-07', 1, 11, 'doctype', 'submitter',
        'submitlog', NULL, NULL, 'en', '{authors}', '{maintainers}',
        '{licensors}', '{parentauthors}', 'analytics code', 'buylink', 10, 1
        ) RETURNING module_ident;''')
        collection_ident = cursor.fetchone()[0]

        subjects = [(2, 'Business',), (3, 'Humanities',)]

        values_expr = ", ".join(["({}, '{}')".format(collection_ident, id)
                                 for id, name in subjects])
        cursor.execute("""INSERT INTO moduletags (module_ident, tagid)
        VALUES {};""".format(values_expr))
        cursor.connection.commit()

        from ..database import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT",
                                         3, collection_ident,
                                         testing.fake_plpy)

        cursor.execute("""\
        SELECT tag
        FROM moduletags NATURAL JOIN tags
        WHERE module_ident = %s""", (new_ident,))

        inserted_subjects = [x[0] for x in cursor.fetchall()]
        self.assertEqual(sorted(inserted_subjects),
                         sorted([name for id, name in subjects]))

    def test_set_version(self):
        from ..database import set_version

        # set_version for modules
        td = {
            'new': {
                'portal_type': 'Module',
                'major_version': 1,
                'minor_version': None,
                'version': '1.13',
                }
            }
        modified = set_version(td['new']['portal_type'], td['new']['version'], td)
        self.assertEqual(modified, 'MODIFY')
        self.assertEqual(td['new'], {
            'portal_type': 'Module',
            'major_version': 13,
            'minor_version': None,
            'version': '1.13',
            })

        # set_version for collections
        td = {
            'new': {
                'portal_type': 'Collection',
                'major_version': 1,
                'minor_version': None,
                'version': '1.100',
                }
            }
        modified = set_version(td['new']['portal_type'], td['new']['version'], td)
        self.assertEqual(modified, 'MODIFY')
        self.assertEqual(td['new'], {
            'portal_type': 'Collection',
            'major_version': 100,
            'minor_version': 1,
            'version': '1.100',
            })

    @testing.plpy_connect
    def test_get_module_uuid(self, plpy):
        from ..database import get_module_uuid
        mod_uuid = get_module_uuid(plpy, 'm41237')
        self.assertEqual(mod_uuid, '91cb5f28-2b8a-4324-9373-dac1d617bc24')

    @testing.plpy_connect
    def test_get_subcols(self, plpy):
        from ..database import get_subcols
        subcols = tuple(get_subcols(4, plpy))
        self.assertEqual(subcols, (22, 25))

    @testing.db_connect
    def test_insert_new_module(self, cursor):
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert abstract
        cursor.execute("INSERT INTO abstracts (abstractid, abstract) VALUES (20802, '')")

        # Insert a new module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name, created, revised, authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent)
        VALUES (
         'm47638',
         'Module',
         '1.13',
         'test convert',
         '2013-12-09T16:57:29Z',
         '2013-12-09T17:14:08Z',
         ARRAY ['user1'],
         ARRAY ['user1'],
         ARRAY ['user1'],
         20802,
         null,
         7,
         '',
         'user1',
         'Created module',
         'en',
         null
        )''')

        # module_republished trigger should not insert anything
        cursor.execute('SELECT COUNT(*) FROM modules')
        n_modules = cursor.fetchone()[0]
        self.assertEqual(n_modules, old_n_modules + 1)

        # Check that major and minor version are set correctly
        cursor.execute('SELECT major_version, minor_version FROM modules ORDER BY module_ident DESC')
        major, minor = cursor.fetchone()
        self.assertEqual(major, 13)
        self.assertEqual(minor, None)

    @testing.db_connect
    def test_collection_minor_updates(self, cursor):
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert a new version of an existing module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name,
         created, revised,
         authors, maintainers, licensors,
         abstractid, stateid, licenseid, doctype, submitter, submitlog,
         language, parent)
        VALUES ('m42955', 'Module', '1.8',
        'New Preface to College Physics',
        '2013-07-31 14:07:20.590652-05' , '2013-07-31 15:07:20.590652-05',
        '{OpenStaxCollege,cnxcap}', '{OpenStaxCollege,cnxcap}', '{OSCRiceUniversity}',
        2, 1, 12, '', 'reedstrm', 'I did not change something',
        'en', NULL) RETURNING module_ident''')

        cursor.connection.commit()

        # Check one minor version for College Physics and Derived Copy have
        # been created
        cursor.execute('SELECT COUNT(*) FROM modules')
        new_n_modules = cursor.fetchone()[0]
        self.assertEqual(new_n_modules, old_n_modules + 3)
        old_n_modules = new_n_modules

        cursor.execute("""\
        SELECT module_version(major_version, minor_version)
        FROM modules
        WHERE portal_type = 'Collection'
        ORDER BY revised DESC, uuid LIMIT 2""")
        self.assertEqual(cursor.fetchall(), [['1.2'], ['7.2']])

        # new collxml for minor versions as well
        cursor.execute("""\
        SELECT count(*)
        FROM module_files
        WHERE filename = 'collection.xml'""")
        self.assertEqual(cursor.fetchall(), [[3]])

        # Compare them
        cursor.execute("""\
        SELECT convert_from(file, 'utf-8')
        FROM module_files natural join files
        WHERE filename = 'collection.xml'
        ORDER BY fileid""")

        for fname in ('collection.xml',
                      'collection_minor_2.xml',
                      'collection_minor_3.xml'):
            filepath = os.path.join(testing.DATA_DIRECTORY, fname)
            with open(filepath) as f:
                expected = f.read()

            result = cursor.fetchone()[0]
            # Remove the revised timestamp from the xml as the dates are going
            # to be different
            result = re.sub('<md:revised>[^<]*</md:revised>',
                            '<md:revised></md:revised>', result)
            expected = re.sub('<md:revised>[^<]*</md:revised>',
                              '<md:revised></md:revised>', expected)
            self.assertEqual(result, expected)

        # Insert a new version of another existing module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name,
         created, revised,
         authors, maintainers, licensors, abstractid, stateid, licenseid, doctype, submitter, submitlog,
         language, parent)
        VALUES ('m42092', 'Module', '1.5',
        'Physics: An Introduction+',
        '2013-07-31 14:07:20.590652-05' , '2013-07-31 15:07:20.590652-05',
        NULL, NULL, NULL, 1, NULL, 1, '', 'reedstrm', 'I did change something',
        'en', NULL) RETURNING module_ident''')
        cursor.connection.commit()

        # Check one more minor version for College Physics, Derived Copy and
        # two SubCollections have been created
        cursor.execute('SELECT COUNT(*) FROM modules')
        new_n_modules = cursor.fetchone()[0]
        self.assertEqual(new_n_modules, old_n_modules + 5)

        cursor.execute("""\
        SELECT module_version(major_version, minor_version)
        FROM modules
        WHERE portal_type IN ('Collection', 'SubCollection')
        ORDER BY revised DESC, uuid LIMIT 4""")

        self.assertEqual(cursor.fetchall(), [['1.2'], ['1.3'], ['7.2'], ['7.3']])

        # Check that new versions of both pages are in the collection tree
        cursor.execute("SELECT tree_to_json(%s, '7.3', FALSE)::JSON",
                       ('e79ffde3-7fb4-4af3-9ec8-df648b391597',))
        tree = cursor.fetchone()[0]
        children = list(flatten_tree_to_ident_hashes(tree))
        self.assertIn('209deb1f-1a46-4369-9e0d-18674cf58a3e@8', children)
        self.assertIn('d395b566-5fe3-4428-bcb2-19016e3aa3ce@5', children)

    @testing.db_connect
    def test_module(self, cursor):
        # Create a fake collated tree for College Physics
        # which contains the module that is going to have a new version
        cursor.execute("""\
INSERT INTO trees (parent_id, documentid, is_collated)
    VALUES (NULL, 1, TRUE) RETURNING nodeid""")
        nodeid = cursor.fetchone()[0]
        cursor.execute("""\
INSERT INTO trees (parent_id, documentid, is_collated)
    VALUES (%s, 2, TRUE)""", (nodeid,))
        cursor.connection.commit()

        # update other collection to have subcollection uuids
        cursor.execute("SELECT subcol_uuids('e79ffde3-7fb4-4af3-9ec8-df648b391597','7.1')")

        cursor.execute('SELECT nodeid FROM trees WHERE documentid = 18')
        old_nodeid = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert a new version of an existing module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name,
         created, revised,
         authors, maintainers, licensors, abstractid, stateid, licenseid, doctype, submitter, submitlog,
         language, parent)
        VALUES ('m42119', 'Module', '1.4',
        'Introduction to Science and the Realm of Physics, Physical Quantities, and Units',
        '2013-07-31 14:07:20.590652-05' , '2013-07-31 15:07:20.590652-05',
        NULL, NULL, NULL, 1, NULL, 11, '', 'reedstrm', 'I did not change something',
        'en', NULL) RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # After the new module is inserted, there should be a new module and two
        # new collections, and two new subcollections
        cursor.execute('SELECT COUNT(*) FROM modules')
        self.assertEqual(cursor.fetchone()[0], old_n_modules + 5)

        # Test that the module inserted has the right major and minor versions
        cursor.execute('''SELECT major_version, minor_version, uuid FROM modules
            WHERE portal_type = 'Module' ORDER BY module_ident DESC''')
        major, minor, uuid = cursor.fetchone()
        self.assertEqual(major, 4)
        self.assertEqual(minor, None)
        # Test that the module inserted has the same uuid as an older version of m42955
        self.assertEqual(uuid, 'f3c9ab70-a916-4d8c-9256-42953287b4e9')

        # Test that the latest row in modules is a collection with updated
        # version
        cursor.execute('SELECT * FROM modules m ORDER BY module_ident DESC')
        results = cursor.fetchone()
        new_collection_id = results['module_ident']

        self.assertEqual(results['portal_type'], 'Collection')
        self.assertEqual(results['name'], '<span style="color:red;">Derived</span>'
                                          ' Copy of College <i>Physics</i>')
        self.assertEqual(results['submitter'], 'reedstrm')
        self.assertEqual(results['submitlog'], 'I did not change something')
        self.assertEqual(results['major_version'], 1)
        self.assertEqual(results['minor_version'], 2)
        self.assertEqual(results['print_style'], None)

        results = cursor.fetchone()
        new_collection_2_id = results['module_ident']

        self.assertEqual(results['portal_type'], 'Collection')
        self.assertEqual(results['name'], 'College Physics')
        self.assertEqual(results['submitter'], 'reedstrm')
        self.assertEqual(results['submitlog'], 'I did not change something')
        self.assertEqual(results['major_version'], 7)
        self.assertEqual(results['minor_version'], 2)
        self.assertEqual(results['print_style'], None)

        results = cursor.fetchone()
        new_subcollection_id = results['module_ident']

        self.assertEqual(results['portal_type'], 'SubCollection')
        self.assertEqual(results['name'], 'Introduction: The Nature of Science and Physics')
        self.assertEqual(results['submitter'], 'reedstrm')
        self.assertEqual(results['submitlog'], 'I did not change something')
        self.assertEqual(results['major_version'], 7)
        self.assertEqual(results['minor_version'], 2)
        self.assertEqual(results['print_style'], None)

        results = cursor.fetchone()
        new_subcollection_2_id = results['module_ident']

        self.assertEqual(results['portal_type'], 'SubCollection')
        self.assertEqual(results['name'], 'Introduction: The Nature of Science and Physics')
        self.assertEqual(results['submitter'], 'reedstrm')
        self.assertEqual(results['submitlog'], 'I did not change something')
        self.assertEqual(results['major_version'], 1)
        self.assertEqual(results['minor_version'], 2)
        self.assertEqual(results['print_style'], None)

        cursor.execute("UPDATE modules SET print_style = '*NEW PRINT STYLE*'"
                       " WHERE abstractid = 1")

        cursor.execute("SELECT print_style FROM modules WHERE abstractid = 1")

        print_style = cursor.fetchone()[0]

        self.assertEqual(print_style, '*NEW PRINT STYLE*')

        cursor.execute('SELECT nodeid FROM trees '
                       'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        new_nodeid = cursor.fetchone()[0]

        sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.nodeid, tr.parent_id, tr.documentid, tr.title,
                   tr.childorder, tr.latest, ARRAY[tr.nodeid]
            FROM trees tr
            WHERE tr.nodeid = %(nodeid)s
        UNION ALL
            SELECT c.nodeid, c.parent_id, c.documentid, c.title,
                   c.childorder, c.latest, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON c.parent_id = t.node
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t'''

        cursor.execute(sql, {'nodeid': old_nodeid})
        old_tree = cursor.fetchall()

        cursor.execute(sql, {'nodeid': new_nodeid})
        new_tree = cursor.fetchall()

        # Test that the new collection tree is identical to the old collection
        # tree except for the new document ids
        self.assertEqual(len(old_tree), len(new_tree))

        # make sure all the node ids are different from the old ones
        old_nodeids = [i[0] for i in old_tree]
        new_nodeids = [i[0] for i in new_tree]
        all_nodeids = old_nodeids + new_nodeids
        self.assertEqual(len(set(all_nodeids)), len(all_nodeids))

        new_document_ids = {
            # old module_ident: new module_ident
            18: new_collection_id,
            1: new_collection_2_id,
            24: new_subcollection_id,
            22: new_subcollection_2_id,
            3: new_module_ident,
            }
        for i, old_node in enumerate(old_tree):
            self.assertEqual(new_document_ids.get(old_node[2], old_node[2]),
                             new_tree[i][2])  # documentid
            self.assertEqual(old_node[3], new_tree[i][3])  # title
            self.assertEqual(old_node[4], new_tree[i][4])  # child order
            self.assertEqual(old_node[5], new_tree[i][5])  # latest

    @testing.db_connect
    def test_module_files_from_cnxml(self, cursor):
        # Insert abstract with cnxml
        cursor.execute('''\
        INSERT INTO abstracts
        (abstractid, abstract)
        VALUES
        (20802, 'Here is my <emphasis>string</emphasis> summary.')
        ''')

        # Insert a new version of an existing module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name, created, revised, authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent)
        VALUES (
        'm42119', 'Module', '1.2', 'New Version', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, NULL, NULL, 20802, NULL, 11, '', NULL, '',
        'en', NULL) RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Make sure there's no fulltext index info
        cursor.execute('''SELECT count(*)
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''\
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''\
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''',
                           (new_module_ident, fileid, filename,))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''\
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
                       (new_module_ident, fileid,))

        # Test that html abstract is generated
        cursor.execute('''SELECT abstract, html FROM abstracts
            WHERE abstractid = 20802''')
        abstract, html = cursor.fetchone()
        self.assertEqual(abstract,
                         'Here is my <emphasis>string</emphasis> summary.')
        self.assertIn('Here is my <strong>string</strong> summary.', html)

        # Get the index.cnxml.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.cnxml.html' ''',
                       (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we generated exactly one index.cnxml.html for new_module_ident
        self.assertEqual(len(index_htmls), 1)
        # Test that the index.cnxml.html contains html
        html = index_htmls[0][0][:]
        self.assertIn('<html', html)

        # Test that the generated index.cnxml.html was processed for fulltext search
        cursor.execute('''SELECT module_idx, fulltext
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        idx, fulltext = cursor.fetchall()[0]
        self.assertEqual(len(idx), 3948)
        self.assertIn('Introduction to Science and the Realm of Physics, '
                      'Physical Quantities, and Units', fulltext)

    @testing.db_connect
    def test_module_files_from_html(self, cursor):
        # Insert abstract with cnxml -- (this is tested elsewhere)
        # This also tests for when a abstract has a resource. The transfomr
        #   happens within when the add_module_file trigger is executed.
        #   This means the resouces should be available.
        abstract = 'Image: <media><image mime-type="image/jpeg" src="Figure_01_00_01.jpg" /></media>'
        cursor.execute("INSERT INTO abstracts (abstractid, abstract) "
                       "VALUES (20802, %s)",
                       (abstract,))

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules
        (moduleid, portal_type, version, name, created, revised, authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent)
        VALUES (
        'm42119', 'Module', '1.2', 'New Version', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, NULL, NULL, 20802, NULL, 11, '', NULL, '',
        'en', NULL) RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Make sure there's no fulltext index info
        cursor.execute('''SELECT count(*)
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Copy files for m42119 except *.html and *.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename NOT LIKE '%.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''', (new_module_ident, fileid, filename,))

        # Insert index.cnxml.html only after adding all the other files
        cursor.execute('''
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml.html'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml.html' ''',
                       (new_module_ident, fileid,))

        # Test that html abstract is generated
        cursor.execute('''SELECT abstract, html FROM abstracts
            WHERE abstractid = 20802''')
        old_abstract, html = cursor.fetchone()
        self.assertEqual(old_abstract, abstract)
        self.assertIn(
            """Image: <span data-type="media"><img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" data-media-type="image/jpeg" alt=""/></span>""",
            html)

        # Get the index.html.cnxml generated by the trigger
        cursor.execute('''SELECT file, filename
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename LIKE %s ''',
                       (new_module_ident, '%.cnxml'))
        index_cnxmls = cursor.fetchall()

        # Test that we generated index.html.cnxml and index.cnxml
        #   for new_module_ident
        self.assertEqual(len(index_cnxmls), 2)
        self.assertEqual(sorted([fn for f, fn in index_cnxmls]),
                         ['index.cnxml', 'index.html.cnxml'])
        # Test that the index.html.cnxml contains cnxml
        cnxml = index_cnxmls[0][0][:]
        self.assertIn('<document', cnxml)

        # Test that the inserted index.cnxml.html was processed for fulltext search
        cursor.execute('''SELECT module_idx, fulltext
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        idx, fulltext = cursor.fetchall()[0]
        self.assertEqual(len(idx), 3922)
        self.assertIn('Introduction to Science and the Realm of Physics, '
                      'Physical Quantities, and Units', fulltext)

    @testing.db_connect
    def test_module_files_overwrite_index_html(self, cursor):
        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules
        (moduleid, portal_type, version, name, created, revised, authors, maintainers, licensors,  abstractid, stateid, licenseid, doctype, submitter, submitlog, language, parent)
        VALUES (
        'm42119', 'Module', '1.2', 'New Version', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, NULL, NULL, 1, NULL, 11, '', NULL, '',
        'en', NULL) RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        self.assertEqual(cursor.fetchone()[0], 0)

        # Create index.cnxml.html to make sure module files trigger will
        # NOT overwrite it
        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        custom_content = 'abcd'
        cursor.execute('''
            INSERT INTO files (file, media_type)
            VALUES (%s, 'text/html') RETURNING fileid''',
                       [custom_content])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
            (module_ident, fileid, filename)
            VALUES (%s, %s, 'index.cnxml.html')''',
                       [new_module_ident, fileid])
        cursor.execute('ALTER TABLE module_files ENABLE TRIGGER ALL')

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''', (new_module_ident, fileid, filename))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
                       (new_module_ident, fileid,))

        # Get the index.cnxml.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.cnxml.html' ''',
                       (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we DID NOT generate an index.cnxml.html for new_module_ident
        self.assertEqual(len(index_htmls), 1)
        # Test that the index.cnxml.html contains the custom content.
        html = index_htmls[0][0][:]
        self.assertEqual(custom_content, html)

    @testing.db_connect
    def test_collated_fulltext_indexing_triggers(self, cursor):
        """Verify that inserting a collated file association builds
        the necessary indexes.  This is used when a book is cooked.
        """

        cursor.execute('INSERT INTO collated_file_associations (context, item, fileid) '
                       'VALUES(18,19,108)')
        # Verify that the inserted file has been indexed
        cursor.execute('SELECT length(module_idx) '
                       'FROM collated_fti '
                       'WHERE context = 18 AND item = 19')
        self.assertEqual(cursor.fetchone()[0], 55)

        cursor.execute("SELECT word "
                       "FROM  ts_stat('SELECT module_idx from collated_fti "
                       "WHERE context = 18 AND item = 19')")
        words = cursor.fetchall()
        self.assertEqual(len(words), 55)
        self.assertIn(['følger'], words)

    @testing.db_connect
    def test_tree_to_json(self, cursor):
        """Verify the results of the ``tree_to_json_for_legacy`` sql function.
        This is used during a cnx-publishing publication.
        """
        expected_tree = {
            u'id': u'col11406',
            u'title': u'College Physics',
            u'version': u'1.7',
            u'contents': [
                {u'id': u'm42955', u'title': u'Preface', u'version': u'1.7'},
                {u'id': u'col15537',
                 u'version': u'1.7',
                 u'title': u'Introduction: The Nature of Science and Physics',
                 u'contents': [
                     {u'id': u'm42119',
                      u'title': u'Introduction to Science and the Realm of '
                                u'Physics, Physical Quantities, and Units',
                      u'version': u'1.3'},
                     {u'id': u'm42092',
                      u'title': u'Physics: An Introduction',
                      u'version': u'1.4'},
                     {u'id': u'm42091',
                      u'title': u'Physical Quantities and Units',
                      u'version': u'1.6'},
                     {u'id': u'm42120',
                      u'title': u'Accuracy, Precision, and Significant '
                                u'Figures',
                      u'version': u'1.7'},
                     {u'id': u'm42121',
                      u'title': u'Approximation',
                      u'version': u'1.5'}]},
                {u'id': u'col15538',
                 u'version': u'1.7',
                 u"title": u"Further Applications of Newton's Laws: Friction,"
                           u" Drag, and Elasticity",
                 u'contents': [
                     {u'id': u'm42138',
                      u'title': u'Introduction: Further Applications of '
                                u'Newton\u2019s Laws',
                      u'version': u'1.2'},
                     {u'id': u'm42139',
                      u'title': u'Friction',
                      u'version': u'1.5'},
                     {u'id': u'm42080',
                      u'title': u'Drag Forces',
                      u'version': u'1.6'},
                     {u'id': u'm42081',
                      u'title': u'Elasticity: Stress and Strain',
                      u'version': u'1.8'}]},
                {u'id': u'm42699',
                 u'title': u'Atomic Masses',
                 u'version': u'1.3'},
                {u'id': u'm42702',
                 u'title': u'Selected Radioactive Isotopes',
                 u'version': u'1.2'},
                {u'id': u'm42720',
                 u'title': u'Useful Inf\xf8rmation',
                 u'version': u'1.5'},
                {u'id': u'm42709',
                 u'title': u'Glossary of Key Symbols and Notation',
                 u'version': u'1.5'}]}
        cursor.execute("""\
SELECT tree_to_json_for_legacy(
    'e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1')::json
""")
        tree = cursor.fetchone()[0]
        self.assertEqual(expected_tree, tree)

    @unittest.skip("Not implemented")
    def test_blank_abstract(self, cursor):
        # Insert blank abstract
        with self.assertRaises(psycopg2.InternalError) as caught_exception:
            cursor.execute("INSERT INTO abstracts (abstractid) "
                           "VALUES (20801)")
        self.assertIn("Blank entry", caught_exception.exception.message)


class UpdateLatestTriggerTestCase(unittest.TestCase):
    """Test case for updating the latest_modules table
    """
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def test_insert_new_module(self, cursor):
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL, NULL) RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)

    @testing.db_connect
    def test_insert_existing_module(self, cursor):
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL, NULL) RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.1', 'Changed name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 17:57:54.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2,NULL,NULL) RETURNING module_ident, uuid''', [uuid])
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)

    @testing.db_connect
    def test_insert_not_latest_version(self, cursor):
        """This test case is specifically written for backfilling, new inserts
        may not mean new versions
        """
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL, NULL)
        RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.3', 'Changed name of m1 again',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 18:05:31.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 3, NULL, NULL)
        RETURNING module_ident, uuid''', [uuid])
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.2', 'Changed name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 17:08:57.000000+02',
        1, 11, '', '', '', DEFAULT, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, NULL, NULL)
        RETURNING module_ident, uuid''', [uuid])

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)


class LegacyCompatTriggerTestCase(unittest.TestCase):
    """Test the legacy compotibilty trigger that fills in legacy data
    coming from contemporary publications.

    Contemporary publications MUST not set the legacy ``version``,
    which defaults to null. They also MUST supply the moduleid,
    but only when making a revision publication, which ties the ``uuid``
    to the legacy ``moduleid``.
    """
    fixture = testing.schema_fixture

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        cursor.execute("""\
INSERT INTO abstracts (abstract) VALUES (' ') RETURNING abstractid""")
        self._abstract_id = cursor.fetchone()[0]

    def tearDown(self):
        self.fixture.tearDown()

    @testing.db_connect
    def test_new_module(self, cursor):
        """Verify publishing of a new module creates values for legacy fields.
        """
        # Insert a new module.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  moduleid,
  major_version,
  minor_version,
  version""", (self._abstract_id,))
        moduleid, major_ver, minor_ver, ver = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(moduleid, 'm10000')
        self.assertEqual(major_ver, 1)
        self.assertEqual(minor_ver, None)
        self.assertEqual(ver, '1.1')

    @testing.db_connect
    def test_new_collection(self, cursor):
        """Verify publishing of a new collection creates values
        for legacy fields.
        """
        # Insert a new collection.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, 'Collection', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  moduleid,
  major_version,
  minor_version,
  version""", (self._abstract_id,))
        moduleid, major_ver, minor_ver, ver = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(moduleid, 'col10000')
        self.assertEqual(major_ver, 1)
        self.assertEqual(minor_ver, 1)
        self.assertEqual(ver, '1.1')

    @testing.db_connect
    def test_module_revision(self, cursor):
        """Verify publishing of a module revision uses legacy field values.
        """
        cursor.execute("SELECT setval('moduleid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'm{}'.format(id_num)  # m10101
        # Insert a new module to base a revision on.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (self._abstract_id,))
        uuid_, moduleid, major_ver, minor_ver, ver = cursor.fetchone()
        self.assertEqual(moduleid, expected_moduleid)

        # Now insert the revision.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (%s, 2, DEFAULT, %s,
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (uuid_, moduleid, self._abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        self.assertEqual(rev_moduleid, expected_moduleid)
        self.assertEqual(ver, '1.1')
        self.assertEqual(rev_major_ver, 2)
        self.assertEqual(rev_minor_ver, None)
        self.assertEqual(rev_ver, '1.2')

    @testing.db_connect
    def test_collection_revision(self, cursor):
        """Verify publishing of a collection revision uses legacy field values.
        """
        cursor.execute("SELECT setval('collectionid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'col{}'.format(id_num)  # col10101
        # Insert a new module to base a revision on.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, 'Collection', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (self._abstract_id,))
        uuid_, moduleid, major_ver, minor_ver, ver = cursor.fetchone()
        self.assertEqual(moduleid, expected_moduleid)

        # Now insert the revision.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (%s, 2, 1, %s,
   DEFAULT, 'Collection', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (uuid_, moduleid, self._abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        self.assertEqual(rev_moduleid, expected_moduleid)
        self.assertEqual(ver, '1.1')
        self.assertEqual(rev_major_ver, 2)
        self.assertEqual(rev_minor_ver, 1)
        self.assertEqual(rev_ver, '1.2')

    @testing.db_connect
    def test_anti_republish_module_on_collection_revision(self, cursor):
        """Verify publishing of a collection revision with modules included
        in other collections. Contemporary publications should not republish
        the modules within the current collections in the publication context.

        Note, contemporary publications do NOT utilize the trigger
        that causes minor republications of collections. This feature
        is only enabled for legacy publications.

        This introduces two collections with a shared module.
        The goal is to publish one of the collections and not have
        the other collection republish.
        """
        cursor.execute("SELECT setval('collectionid_seq', 10100)")
        id_num = cursor.fetchone()[0]
        expected_col_one_id = 'col{}'.format(id_num + 1)  # col10101
        expected_col_two_id = 'col{}'.format(id_num + 2)  # col10102
        cursor.execute("SELECT setval('moduleid_seq', 10100)")
        id_num = cursor.fetchone()[0]
        expected_m_one_id = 'm{}'.format(id_num + 1)  # m10101
        expected_m_two_id = 'm{}'.format(id_num + 2)  # m10102

        entries = [expected_m_one_id, expected_m_two_id,
                   expected_col_one_id, expected_col_two_id,
                   ]
        for mid in entries:
            portal_type = mid.startswith('m') and 'Module' or 'Collection'
            # Insert a new module to base a revision on.
            cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, %s, %s,
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  module_ident,
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (portal_type, "title for {}".format(mid), self._abstract_id,))
            ident, uuid_, moduleid, major_ver, minor_ver, ver = cursor.fetchone()
            self.assertEqual(moduleid, mid)

            if portal_type == 'Collection':
                args = (ident, "**{}**".format(moduleid),)
                cursor.execute("""\
INSERT INTO trees
  (nodeid, parent_id, documentid, title, childorder, latest)
VALUES
  (DEFAULT, NULL, %s, %s, DEFAULT, DEFAULT)
RETURNING nodeid""", args)
                root_node_id = cursor.fetchone()[0]
                # Insert the tree for the collections.
                for i, sub_mid in enumerate(entries[:2]):
                    decendents = entries[2:]
                    args = (root_node_id, sub_mid, sub_mid, i,)
                    cursor.execute("""\
INSERT INTO trees
  (nodeid, parent_id,
   documentid,
   title, childorder, latest)
VALUES
  (DEFAULT, %s,
   (select module_ident from latest_modules where moduleid = %s),
   %s, %s, DEFAULT)""", args)

        # Now insert a revision.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  ((SELECT uuid FROM latest_modules WHERE moduleid = %s),
   2, NULL, %s,
   DEFAULT, 'Module', ' MOO ',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid,
  moduleid,
  major_version,
  minor_version,
  version""", (expected_m_one_id, expected_m_one_id, self._abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        self.assertEqual(rev_moduleid, expected_m_one_id)
        self.assertEqual(rev_major_ver, 2)
        self.assertEqual(rev_minor_ver, None)
        self.assertEqual(rev_ver, '1.2')

        # Lastly check that no republications took place.
        # This can be done by simply counting the entries. We inserted
        # four entries (two modules and two collections) and one revision.
        cursor.execute("""\
SELECT portal_type, count(*)
FROM modules
GROUP BY portal_type""")
        counts = dict(cursor.fetchall())
        expected_counts = {
            'Module': 3,
            'Collection': 2,
            }
        self.assertEqual(counts, expected_counts)

    @testing.db_connect
    def test_new_module_wo_uuid(self, cursor):
        """Verify legacy publishing of a new module creates a UUID
        and licenseid in a 'document_controls' entry.
        """
        # Insert a new module.
        cursor.execute("""\
INSERT INTO modules
  (uuid, major_version, minor_version, moduleid,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid, licenseid""", (self._abstract_id,))
        uuid_, license_id = cursor.fetchone()

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("SELECT uuid, licenseid from document_controls")
        try:
            controls_uuid, controls_license_id = cursor.fetchone()
        except TypeError:
            self.fail("the document_controls entry was not made.")

        # Check the values match
        self.assertEqual(uuid_, controls_uuid)
        self.assertEqual(license_id, controls_license_id)

    @testing.db_connect
    def test_new_module_user_upsert(self, cursor):
        """Verify legacy publishing of a new module upserts users
        from the persons table into the users table.
        """
        # Insert the legacy persons records.
        #   These people would have registered on legacy after the initial
        #   migration of legacy users.
        cursor.execute("""\
INSERT INTO persons
  (personid, honorific, firstname, surname, fullname)
VALUES
  ('cnxcap', NULL, 'College', 'Physics', 'OSC Physics Maintainer'),
  ('legacy', NULL, 'Legacy', 'User', 'Legacy User'),
  ('ruins', NULL, 'Legacy', 'Ruins', 'Legacy Ruins')
""")
        # Insert one existing user into the users shadow table.
        cursor.execute("""\
INSERT INTO users (username, first_name, last_name, full_name, is_moderated)
VALUES ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer', 't')""")
        # Insert a new legacy module.
        cursor.execute("""\
INSERT INTO modules
  (moduleid, version,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, '1.1',
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{legacy}', '{cnxcap}', '{ruins}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  uuid, licenseid""", (self._abstract_id,))
        uuid_, license_id = cursor.fetchone()

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("""\
SELECT username, first_name, last_name, full_name
FROM users
WHERE username = any('{legacy, ruins}'::text[])
ORDER BY username
""")
        user_records = cursor.fetchall()

        # Check for the upsert.
        self.assertEqual(user_records[0],
                         ['legacy', 'Legacy', 'User', 'Legacy User'])
        self.assertEqual(user_records[1],
                         ['ruins', 'Legacy', 'Ruins', 'Legacy Ruins'])

    @testing.db_connect
    def test_update_user_update(self, cursor):
        """Verify legacy updating of user account also updates rewrite
        """
        # Insert the legacy persons records.
        #   This person would have registered on legacy already, so we insert them there too.
        cursor.execute("""\
            INSERT INTO persons
            (personid, firstname, surname, fullname)
            VALUES
            ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer')
        """)
        cursor.execute("""\
            INSERT INTO users
            (username, first_name, last_name, full_name)
            VALUES
            ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer')
        """)

        # Update user profile on legacy
        cursor.execute("""\
            UPDATE persons
            SET firstname = 'Univeristy',
                surname = 'Maths',
                fullname = 'OSC Maths Maintainer'
            WHERE personid = 'cnxcap'
        """)

        # Grab the user from users table to verify it's updated
        cursor.execute("""\
            SELECT username, first_name, last_name, full_name
            FROM users
            WHERE username = 'cnxcap'
        """)
        rewrite_user_record = cursor.fetchone()

        # Check for the update.
        self.assertEqual(rewrite_user_record, ['cnxcap', 'Univeristy', 'Maths', 'OSC Maths Maintainer'])

    @testing.db_connect
    def test_new_moduleoptionalroles_user_insert(self, cursor):
        """Verify publishing of a new moduleoptionalroles record
        inserts users from the persons table into the users table.
        This should only insert new records and leave the existing
        records as they are, because we have no way of telling whether
        the publication was by legacy or cnx-publishing.
        """
        # Insert the legacy persons records.
        #   These people would have registered on legacy after the initial
        #   migration of legacy users.
        # The '***' on the cnxcap user is to test that the users record
        #   is not updated from the persons record.
        cursor.execute("""\
INSERT INTO persons
  (personid, honorific, firstname, surname, fullname)
VALUES
  ('cnxcap', NULL, '*** College ***', '*** Physics ***',
   '*** OSC Physics Maintainer ***'),
  ('legacy', NULL, 'Legacy', 'User', 'Legacy User'),
  ('ruins', NULL, 'Legacy', 'Ruins', 'Legacy Ruins')
""")
        # Insert one existing user into the users shadow table.
        cursor.execute("""\
INSERT INTO users (username, first_name, last_name, full_name, is_moderated)
VALUES ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer', 't')""")
        # Insert a new legacy module.
        cursor.execute("""\
INSERT INTO modules
  (moduleid, version,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  (DEFAULT, '1.1',
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{legacy}', '{legacy}', '{legacy}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  module_ident, uuid, licenseid""", (self._abstract_id,))
        module_ident, uuid_, license_id = cursor.fetchone()
        # Insert the moduleoptionalroles records.
        cursor.execute("""\
INSERT INTO moduleoptionalroles (module_ident, roleid, personids)
VALUES (%s, 4, '{cnxcap, ruins}')""", (module_ident,))

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("""\
SELECT username, first_name, last_name, full_name
FROM users
ORDER BY username
""")
        user_records = cursor.fetchall()

        # Check for the record set...
        # The cnxcap user should not have been updated.
        self.assertEqual([x[0] for x in user_records],
                         ['cnxcap', 'legacy', 'ruins'])
        self.assertEqual(
            user_records[0],
            ['cnxcap', 'College', 'Physics', 'OSC Physics Maintainer'])
        self.assertEqual(user_records[1],
                         ['legacy', 'Legacy', 'User', 'Legacy User'])
        # The ruins user will be a newly inserted record, copied from
        #   the persons record.
        self.assertEqual(user_records[2],
                         ['ruins', 'Legacy', 'Ruins', 'Legacy Ruins'])


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
                         ['c8ee8dc5-bb73-47c8-b10f-3f37123cf607', 9, 3, 2])
        self.assertEqual(hit_ranks[3],  # row that combines two idents.
                         ['88cd206d-66d2-48f9-86bb-75d5366582ee', 54, 9, 4])

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
                         ['88cd206d-66d2-48f9-86bb-75d5366582ee', 67, 6.7, 3])
        # Note, this module has fewer hits in total, but more on average,
        #   which expectedly boosts its rank.
        self.assertEqual(hit_ranks[3],
                         ['dd7b92c2-e82e-43bb-b224-accbc3cd395a', 39, 7.8, 4])
