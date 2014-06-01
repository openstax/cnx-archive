# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import datetime
import time
import unittest

import psycopg2
from . import *


class InitializeDBTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_initdb_on_already_initialized_db(self):
        # Case for testing the `initdb` raises a discernible error
        #   when the the database is already initialized.
        # The fixture has initialized the database, so we only need to
        #   run the function.
        from ..database import initdb
        settings = get_app_settings(TESTING_CONFIG)
        with self.assertRaises(psycopg2.InternalError) as caught_exception:
            initdb(settings)
        self.assertEqual(caught_exception.exception.message,
                         'Database is already initialized.\n')


class MiscellaneousFunctionsTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def test_iso8601(self, cursor):
        # Exams the iso8601 SQL function.
        cursor.execute("SELECT date_trunc('second', current_timestamp), iso8601(current_timestamp);")
        current, iso8601 = cursor.fetchone()
        # We need to make the date timezone aware, which is what the 'Z' does,
        #   but the parsing statement can't do anything with that.
        # We'll use psycopg2's tzinfo classes for simplicity.
        from psycopg2.tz import FixedOffsetTimezone
        value = datetime.datetime(*time.strptime(iso8601,
                                                 "%Y-%m-%dT%H:%M:%SZ")[:6],
                                   tzinfo=FixedOffsetTimezone())
        self.assertEqual(current, value)


class ModulePublishTriggerTestCase(unittest.TestCase):
    """Tests for the postgresql triggers when a module is published
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def test_get_current_module_ident(self, cursor):
        cursor.execute("""ALTER TABLE modules DISABLE TRIGGER module_insert""")

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

        module_ident = cursor.fetchone()[0]

        self.assertEqual(get_current_module_ident('m1', cursor=cursor),
                module_ident)

    @db_connect
    def test_next_version(self, cursor):
        cursor.execute("""ALTER TABLE modules DISABLE TRIGGER module_insert""")

        from ..database import next_version

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, 1) RETURNING module_ident''')
        module_ident = cursor.fetchone()[0]

        self.assertEqual(next_version(module_ident, cursor=cursor), 2)

    @db_connect
    def test_get_collections(self, cursor):
        cursor.execute("""ALTER TABLE modules DISABLE TRIGGER module_insert""")

        from ..database import get_collections

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c1', DEFAULT, '1.9', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 9, 1) RETURNING module_ident''')
        collection_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c2', DEFAULT, '1.8', 'Name of c1',
        '2013-07-31 12:00:00.000000+01', '2013-10-03 20:00:00.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 8, 1) RETURNING module_ident''')
        collection2_ident = cursor.fetchone()[0]

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.2', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
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

        self.assertEqual(list(get_collections(module_ident, cursor=cursor)),
                [collection_ident, collection2_ident])

    @db_connect
    def test_rebuild_collection_tree(self, cursor):
        cursor.execute("""ALTER TABLE modules DISABLE TRIGGER module_insert""")

        from ..database import rebuild_collection_tree

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c1', DEFAULT, '1.9', 'Name of c1',
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
        DEFAULT, 'Collection', 'c1', DEFAULT, '1.9', 'Name of c1',
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

        new_document_id_map = {
                collection_ident: new_collection_ident,
                module_ident: new_module_ident
                }
        rebuild_collection_tree(collection_ident, new_document_id_map,
                cursor=cursor)

        cursor.execute('''
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
        self.assertEqual(cursor.fetchall(), [(new_collection_ident,),
            (new_module_ident,), (module2_ident,)])

    @db_connect
    def test_republish_collection(self, cursor):
        cursor.execute("""ALTER TABLE modules DISABLE TRIGGER module_insert""")

        from ..database import republish_collection

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c1', '3a5344bd-410d-4553-a951-87bccd996822',
        '1.10', 'Name of c1', '2013-07-31 12:00:00.000000-07',
        '2013-10-03 21:59:12.000000-07', 1, 11, 'doctype', 'submitter',
        'submitlog', NULL, NULL, 'en', '{authors}', '{maintainers}',
        '{licensors}', '{parentauthors}', 'analytics code', 'buylink', 10, 1
        ) RETURNING module_ident''')
        collection_ident = cursor.fetchone()[0]

        new_ident = republish_collection(3, collection_ident, cursor=cursor)

        cursor.execute('''SELECT * FROM modules WHERE
        module_ident = %s''', [new_ident])
        data = cursor.fetchone()
        self.assertEqual(data[1], 'Collection')
        self.assertEqual(data[2], 'c1')
        self.assertEqual(data[3], '3a5344bd-410d-4553-a951-87bccd996822')
        self.assertEqual(data[4], '1.10')
        self.assertEqual(data[5], 'Name of c1')
        self.assertEqual(str(data[6]), '2013-07-31 12:00:00-07:00')
        self.assertNotEqual(str(data[7]), '2013-10-03 21:59:12-07:00')
        self.assertEqual(data[8], 1)
        self.assertEqual(data[9], 11)
        self.assertEqual(data[10], 'doctype')
        self.assertEqual(data[11], 'submitter')
        self.assertEqual(data[12], 'submitlog')
        self.assertEqual(data[13], None)
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

    @db_connect
    def test_republish_collection_w_keywords(self, cursor):
        # Ensure association of the new collection with existing keywords.
        settings = get_app_settings(TESTING_CONFIG)
        from ..database import CONNECTION_SETTINGS_KEY
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute("""
ALTER TABLE modules DISABLE TRIGGER module_insert""")

        from ..database import republish_collection

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c1', '3a5344bd-410d-4553-a951-87bccd996822',
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
        self.db_connection.commit()

        new_ident = republish_collection(3, collection_ident, cursor=cursor)

        cursor.execute("""\
        SELECT word
        FROM modulekeywords NATURAL JOIN keywords
        WHERE module_ident = %s""",
            (new_ident,))
        inserted_keywords = [x[0] for x in cursor.fetchall()]
        self.assertEqual(sorted(inserted_keywords), sorted(keywords))

    @db_connect
    def test_republish_collection_w_subjects(self, cursor):
        # Ensure association of the new collection with existing keywords.
        settings = get_app_settings(TESTING_CONFIG)
        from ..database import CONNECTION_SETTINGS_KEY
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute("""
ALTER TABLE modules DISABLE TRIGGER module_insert""")

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Collection', 'c1', '3a5344bd-410d-4553-a951-87bccd996822',
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
        self.db_connection.commit()

        from ..database import republish_collection
        new_ident = republish_collection(3, collection_ident, cursor=cursor)

        cursor.execute("""\
        SELECT tag
        FROM moduletags NATURAL JOIN tags
        WHERE module_ident = %s""",
            (new_ident,))
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

    @db_connect
    def test_insert_new_module(self, cursor):
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert abstract
        cursor.execute("INSERT INTO abstracts (abstractid, abstract) VALUES (20802, '')")

        # Insert a new module
        cursor.execute('''
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

    @db_connect
    def test_module(self, cursor):
        cursor.execute('SELECT nodeid FROM trees WHERE documentid = 18')
        old_nodeid = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]
        self.assertEqual(old_n_modules, 18)

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules
        (moduleid, portal_type, version, name,
         created, revised,
         authors, maintainers, licensors, abstractid, stateid, licenseid, doctype, submitter, submitlog, 
         language, parent)
        VALUES ('m42955', 'Module', '1.2', 'Preface to College Physics',
        '2013-09-13 15:10:43.000000+02' , '2013-09-13 15:10:43.000000+02',
        NULL, NULL, NULL, 1, NULL, 11, '', NULL, '',
        'en', NULL) RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]

        # After the new module is inserted, there should be a new module and two
        # new collections
        cursor.execute('SELECT COUNT(*) FROM modules')
        self.assertEqual(cursor.fetchone()[0], old_n_modules + 3)

        # Test that the module inserted has the right major and minor versions
        cursor.execute('''SELECT major_version, minor_version, uuid FROM modules 
            WHERE portal_type = 'Module' ORDER BY module_ident DESC''')
        major, minor, uuid = cursor.fetchone()
        self.assertEqual(major, 2)
        self.assertEqual(minor, None)
        # Test that the module inserted has the same uuid as an older version of m42955
        self.assertEqual(uuid, '209deb1f-1a46-4369-9e0d-18674cf58a3e')


        # Test that the latest row in modules is a collection with updated
        # version
        cursor.execute('SELECT * FROM modules m ORDER BY module_ident DESC')
        results = cursor.fetchone()
        new_collection_id = results[0]
        self.assertEqual(results[1], 'Collection') # portal_type
        self.assertEqual(results[5], 'Derived Copy of College Physics') # name
        self.assertEqual(results[-2], 1) # major_version
        self.assertEqual(results[-1], 2) # minor_version

        cursor.execute('SELECT nodeid FROM trees '
                'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        new_nodeid = cursor.fetchone()[0]

        sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr WHERE tr.nodeid = %(nodeid)s
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
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
                2: new_module_ident,
                }
        for i, old_node in enumerate(old_tree):
            self.assertEqual(new_document_ids.get(old_node[2], old_node[2]),
                    new_tree[i][2]) # documentid
            self.assertEqual(old_node[3], new_tree[i][3]) # title
            self.assertEqual(old_node[4], new_tree[i][4]) # child order
            self.assertEqual(old_node[5], new_tree[i][5]) # latest

    @db_connect
    def test_module_files(self, cursor):
        # Insert abstract with cnxml
        cursor.execute('''
        INSERT INTO abstracts 
        (abstractid, abstract) 
        VALUES 
        (20802, 'Here is my <emphasis>string</emphasis> summary.')
        ''')

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

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, m.mimetype
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, mimetype in cursor.fetchall():
            cursor.execute('''INSERT INTO files (file) VALUES (%s)
            RETURNING fileid''', (data,))
            fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            VALUES (%s, %s, %s, %s)''', (new_module_ident, fileid, filename,
                mimetype))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''
        INSERT INTO files (file)
            SELECT f.file
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml'
        RETURNING fileid
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            SELECT %s, %s, m.filename, m.mimetype
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
            (new_module_ident, fileid,))

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
        self.assert_('<html' in html)

        # Test that html abstract is generated
        cursor.execute('''SELECT abstract, html FROM abstracts
            WHERE abstractid = 20802''')
        abstract, html = cursor.fetchone()
        self.assertEqual(abstract,
                'Here is my <emphasis>string</emphasis> summary.')
        self.assert_('Here is my <strong class="emphasis">string</strong> summary.'
                in html)

    @db_connect
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
        # overwrite it
        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        cursor.execute('INSERT INTO files (file) VALUES (%s) RETURNING fileid',
                       ['abcd'])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
            (module_ident, fileid, filename, mimetype)
            VALUES (%s, %s, 'index.cnxml.html', 'text/html')''',
            [new_module_ident, fileid])
        cursor.execute('ALTER TABLE module_files ENABLE TRIGGER ALL')

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, m.mimetype
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, mimetype in cursor.fetchall():
            cursor.execute('''INSERT INTO files (file) VALUES (%s)
            RETURNING fileid''', (data,))
            fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            VALUES (%s, %s, %s, %s)''', (new_module_ident, fileid, filename,
                mimetype))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''
        INSERT INTO files (file)
            SELECT f.file
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml'
        RETURNING fileid
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename, mimetype)
            SELECT %s, %s, m.filename, m.mimetype
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
            (new_module_ident, fileid,))

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
        self.assert_('<html' in html)


class UpdateLatestTriggerTestCase(unittest.TestCase):
    """Test case for updating the latest_modules table
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def test_insert_new_module(self, cursor):
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL) RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)

    @db_connect
    def test_insert_existing_module(self, cursor):
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL) RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.1', 'Changed name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 17:57:54.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, NULL) RETURNING module_ident, uuid''', [uuid])
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)

    @db_connect
    def test_insert_not_latest_version(self, cursor):
        """This test case is specifically written for backfilling, new inserts
        may not mean new versions
        """
        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, '1.1', 'Name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL)
        RETURNING module_ident, uuid''')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.1', 'Changed name of m1 again',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 18:05:31.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 3, NULL)
        RETURNING module_ident, uuid''', [uuid])
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', %s, '1.1', 'Changed name of m1',
        '2013-07-31 12:00:00.000000+02', '2013-10-14 17:08:57.000000+02',
        1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 2, NULL)
        RETURNING module_ident, uuid''', [uuid])

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        self.assertEqual(cursor.fetchone()[0], module_ident)


class LegacyCompatTriggerTestCase(unittest.TestCase):
    """Test the legacy compotibilty trigger that fills in legacy data
    coming from contemporary publications.
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        cursor.execute("""\
INSERT INTO abstracts (abstract) VALUES (' ') RETURNING abstractid""")
        self._abstract_id = cursor.fetchone()[0]

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def make_dummy_module(self, cursor, uuid=None,
                          major_version=None, minor_version=None):
        format_args = {}
        params = [self._abstract_id]
        if uuid is not None:
            format_args['uuid'] = '%s'
            parmas.insert(0, uuid)
        else:
            format_args['uuid'] = 'DEFAULT'
        if major_version is not None:
            format_args['major_version'] = '%s'
            parmas.insert(1, major_version)
        else:
            format_args['major_version'] = 'DEFAULT'
        if minor_version is not None:
            format_args['minor_version'] = '%s'
            parmas.insert(1, minor_version)
        else:
            format_args['minor_version'] = 'DEFAULT'

        statement = """\
INSERT INTO modules
  (uuid, major_version, minor_version,
   module_ident, portal_type, name, created, revised, language,
   submitter, submitlog,
   abstractid, licenseid, parent, parentauthors,
   authors, maintainers, licensors,
   google_analytics, buylink,
   stateid, doctype)
VALUES
  ({uuid}, {major_version}, {minor_version},
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
  version""".format(format_args)

        cusor.execute(statement, params)
        uuid, moduleid, version = cursor.fetchone()
        return uuid, moduleid, version

    @db_connect
    def test_new_module(self, cursor):
        """Verify publishing of a new module creates values for legacy fields.
        """
        # Insert a new module.
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
   DEFAULT, 'Module', 'Plug into the collective conscious',
   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
   'publisher', 'published',
   %s, 11, DEFAULT, DEFAULT,
   '{smoo, fred}', DEFAULT, '{smoo, fred}',
   DEFAULT, DEFAULT,
   DEFAULT, ' ')
RETURNING
  moduleid,
  version""", (self._abstract_id,))
        moduleid, version = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(moduleid, 'm10000')
        self.assertEqual(version, '1.1')

    @db_connect
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
  version""", (self._abstract_id,))
        moduleid, version = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(moduleid, 'col10000')
        self.assertEqual(version, '1.1')

    @db_connect
    def test_module_revision(self, cursor):
        """Verify publishing of a module revision uses legacy field values.
        """
        cursor.execute("SELECT setval('moduleid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'm{}'.format(id_num)  # m10101
        # Insert a new module to base a revision on.
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
  version""", (self._abstract_id,))
        uuid_, moduleid, version = cursor.fetchone()

        # Now insert the revision.
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
  (%s, 2, DEFAULT,
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
  version""", (uuid_, self._abstract_id,))
        rev_uuid_, rev_moduleid, rev_version = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(rev_moduleid, expected_moduleid)
        self.assertEqual(version, '1.1')
        self.assertEqual(rev_version, '1.2')

    @db_connect
    def test_collection_revision(self, cursor):
        """Verify publishing of a collection revision uses legacy field values.
        """
        cursor.execute("SELECT setval('collectionid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'col{}'.format(id_num)  # col10101
        # Insert a new module to base a revision on.
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
  uuid,
  moduleid,
  version""", (self._abstract_id,))
        uuid_, moduleid, version = cursor.fetchone()

        # Now insert the revision.
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
  (%s, 1, 2,
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
  version""", (uuid_, self._abstract_id,))
        rev_uuid_, rev_moduleid, rev_version = cursor.fetchone()

        # Check the fields where correctly assigned.
        self.assertEqual(rev_moduleid, expected_moduleid)
        self.assertEqual(version, '1.1')
        self.assertEqual(rev_version, '1.1')


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
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        from ..utils import parse_app_settings
        cls.settings = parse_app_settings(TESTING_CONFIG)
        from ..database import CONNECTION_SETTINGS_KEY
        cls.db_connection_string = cls.settings[CONNECTION_SETTINGS_KEY]

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        cursor.execute(SQL_FOR_HIT_DOCUMENTS)

    def tearDown(self):
        self.fixture.tearDown()

    @db_connect
    def override_recent_date(self, cursor):
        # Override the SQL function for acquiring the recent date,
        #   because otherwise the test will be a moving target in time.
        cursor.execute("CREATE OR REPLACE FUNCTION get_recency_date () "
                       "RETURNS TIMESTAMP AS $$ BEGIN "
                       "  RETURN '2013-10-20'::timestamp with time zone; "
                       "END; $$ LANGUAGE plpgsql;")

    @db_connect
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

    @db_connect
    def test_recency_function(self, cursor):
        # Exam the function out puts a date.

        # At the time of this writting the recency is one week.
        from datetime import datetime, timedelta
        then = datetime.today() - timedelta(7)

        cursor.execute("SELECT get_recency_date();")
        value = cursor.fetchone()[0]
        # We're mostly checking by the day rather than by time,
        #   so checking by date should be sufficient.
        self.assertEqual(then.date(), value.date())

    def test_hit_average_function(self):
        # Verify the hit average is output in both overall and recent
        #   circumstances.
        self.override_recent_date()
        hits = self.create_hits()

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT hit_average(1, NULL);")
                average = cursor.fetchone()[0]
                cursor.execute("SELECT hit_average(1, 't');")
                recent_average = cursor.fetchone()[0]
                cursor.execute("SELECT hit_average(6, 'f');")
                other_average = cursor.fetchone()[0]
        self.assertEqual(average, sum(hits[1]) / 5.0)
        from math import ceil
        close_enough = lambda d: ceil(d * 1000) / 1000
        self.assertEqual(close_enough(recent_average),
                         close_enough(sum(hits[1][2:]) / 3.0))
        self.assertEqual(close_enough(other_average),
                         close_enough(sum(hits[6]) / 5.0))

    def test_hit_rank_function(self):
        # Verify the hit rank is output in both overall and recent
        #   circumstances.
        self.override_recent_date()
        hits = self.create_hits()

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT hit_rank(5, 'f');")
                rank = cursor.fetchone()[0]
                cursor.execute("SELECT hit_rank(5, 't');")
                recent_rank = cursor.fetchone()[0]
        self.assertEqual(rank, 5)
        self.assertEqual(recent_rank, 3)

    def test_update_recent_hits_function(self):
        # Verify the function updates the recent hit ranks table
        #   with hit rank information grouped by document uuid.
        self.override_recent_date()
        hits = self.create_hits()

        # Call the target SQL function.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT update_hit_ranks();")
                cursor.execute("SELECT * FROM recent_hit_ranks "
                               "ORDER BY rank ASC;")
                hit_ranks = cursor.fetchall()

        self.assertEqual(hit_ranks[1],
                         ('c8ee8dc5-bb73-47c8-b10f-3f37123cf607', 9, 3, 2))
        self.assertEqual(hit_ranks[3],  # row that combines two idents.
                         ('88cd206d-66d2-48f9-86bb-75d5366582ee', 54, 9, 4))

    def test_update_recent_hits_function(self):
        # Verify the function updates the overall hit ranks table
        #   with hit rank information grouped by document uuid.
        self.override_recent_date()
        hits = self.create_hits()

        # Call the target SQL function.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
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
