# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest

from . import *


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

        module_ident = cursor.fetchone()[0]

        self.assertEqual(get_current_module_ident('m1', cursor=cursor),
                module_ident)

    @db_connect
    def test_next_version(self, cursor):
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

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
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

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
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

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
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

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
    def test_insert_new_module(self, cursor):
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert a new module
        cursor.execute('''
        INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm1', DEFAULT, NULL, 'Name of m1',
        '2013-10-14 17:41:40.000000+02', '2013-10-14 17:41:40.000000+02',
        NULL, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
        NULL, NULL, NULL, 1, NULL
        )''')

        # module_republished trigger should not insert anything
        cursor.execute('SELECT COUNT(*) FROM modules')
        n_modules = cursor.fetchone()[0]
        self.assertEqual(n_modules, old_n_modules + 1)

    @db_connect
    def test_module(self, cursor):
        cursor.execute('SELECT nodeid FROM trees '
                       'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        old_nodeid = cursor.fetchone()[0]

        cursor.execute('SELECT fileid '
                       'FROM module_files WHERE module_ident = 1')
        old_files = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]
        self.assertEqual(old_n_modules, 16)

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm42955', '209deb1f-1a46-4369-9e0d-18674cf58a3e', NULL,
        'Preface to College Physics', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, 11, '', '', '', NULL, NULL,
        'en', '{}', '{}', '{}', NULL, NULL, NULL, 2, 0) RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]

        # After the new module is inserted, there should be a new module and a
        # new collection
        cursor.execute('SELECT COUNT(*) FROM modules')
        self.assertEqual(cursor.fetchone()[0], 18)

        # Test that the latest row in modules is a collection with updated
        # version
        cursor.execute('SELECT * FROM modules m ORDER BY module_ident DESC')
        results = cursor.fetchone()
        new_collection_id = results[0]
        self.assertEqual(results[1], 'Collection') # portal_type
        self.assertEqual(results[5], 'College Physics') # name
        self.assertEqual(results[-2], 1) # major_version
        self.assertEqual(results[-1], 8) # minor_version

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
                1: new_collection_id,
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
        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules VALUES (
        DEFAULT, 'Module', 'm42119', 'f3c9ab70-a916-4d8c-9256-42953287b4e9', NULL,
        'New Version', '2013-09-13 15:10:43.000000+02' ,
        '2013-09-13 15:10:43.000000+02', NULL, 11, '', '', '', NULL, NULL,
        'en', '{}', '{}', '{}', NULL, NULL, NULL, 2, NULL) RETURNING module_ident''')

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

        # Get the index.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.html' ''',
        (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we generated exactly one index.html for new_module_ident
        self.assertEqual(len(index_htmls), 1)
        # Test that the index.html contains html
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
