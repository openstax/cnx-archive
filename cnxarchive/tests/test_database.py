# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest
import urllib2
import uuid
from io import StringIO

from . import *


class GetBuylinksTestCase(unittest.TestCase):
    """Tests for the get_buylinks script
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())

        # Mock commandline arguments for ..scripts.get_buylinks.main
        self.argv = [TESTING_CONFIG]

        # Mock response from plone site:
        # responses should be assigned to self.responses by individual tests
        self.responses = ['']
        self.response_id = -1
        def urlopen(url):
            self.response_id += 1
            return StringIO(unicode(self.responses[self.response_id]))
        original_urlopen = urllib2.urlopen
        urllib2.urlopen = urlopen
        self.addCleanup(setattr, urllib2, 'urlopen', original_urlopen)

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self):
        from ..scripts import get_buylinks
        return get_buylinks.main(self.argv)

    @db_connect
    def get_buylink_from_db(self, cursor, collection_id):
        from ..utils import parse_app_settings
        settings = parse_app_settings(TESTING_CONFIG)
        cursor.execute(
                'SELECT m.buylink FROM modules m WHERE m.moduleid = %(moduleid)s;',
                {'moduleid': collection_id})
        return cursor.fetchone()[0]

    def test(self):
        self.argv.append('col11406')
        self.argv.append('m42955')
        self.responses = [
                # response for col11406
                "[('title', ''), "
                "('buyLink', 'http://buy-col11406.com/download')]",
                # response for m42955
                "[('title', ''), "
                "('buyLink', 'http://buy-m42955.com/')]"]
        self.call_target()

        self.assertEqual(self.get_buylink_from_db('col11406'),
                'http://buy-col11406.com/download')
        self.assertEqual(self.get_buylink_from_db('m42955'),
                'http://buy-m42955.com/')

    def test_no_buylink(self):
        self.argv.append('m42955')
        self.response = "[('title', '')]"
        self.call_target()

        self.assertEqual(self.get_buylink_from_db('m42955'), None)

    def test_collection_not_in_db(self):
        self.argv.append('col11522')
        self.response = ("[('title', ''), "
                "('buyLink', 'http://buy-col11522.com/download')]")
        # Just assert that the script does not fail
        self.call_target()


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


class CollectionMigrationTestCase(unittest.TestCase):
    """Tests for creating collection minor versions for collections that are
    already in the database
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
            cursor.execute(fb.read())
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

    def tearDown(self):
        self.fixture.tearDown()

    def insert_modules(self, cursor, modules):
        # modules should be a list of (portal_type, moduleid, uuid, version,
        # name, revised, major_version, minor_version)
        for m in modules:
            cursor.execute('''INSERT INTO modules VALUES (
            DEFAULT, %s, %s, %s, %s, %s, '2013-07-31 00:00:00.000000+02',
            %s, 1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}', NULL,
            NULL, NULL, %s, %s) RETURNING module_ident''', m)
            yield cursor.fetchone()[0]

    def create_collection_tree(self, cursor, relationships):
        # relationships should look like this:
        # ((parent_module_ident, child_module_ident), ...)
        # parent_module_ident should be None for the root
        childorder = 0
        module_ident_to_nodeid = {}
        for parent_module_ident, child_module_ident in relationships:
            cursor.execute('''INSERT INTO trees VALUES (
            DEFAULT, %s, %s, '', %s, NULL) RETURNING nodeid''', [
                module_ident_to_nodeid.get(parent_module_ident, None),
                child_module_ident, childorder])
            childorder += 1
            module_ident_to_nodeid[child_module_ident] = cursor.fetchone()[0]

    @db_connect
    def test_no_minor_version(self, cursor):
        """Test case for when it is not necessary to create a minor version for
        a collection
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        m1_uuid = str(uuid.uuid4())
        m2_uuid = str(uuid.uuid4())
        c1_uuid = str(uuid.uuid4())
        module_idents = list(self.insert_modules(cursor, (
            # portal_type, moduleid, uuid, version, name, revised,
            # major_version, minor_version
            ('Module', 'm1', m1_uuid, '1.1', 'Name of module m1',
                '2013-10-01 11:24:00.000000+02', 1, 1),
            ('Module', 'm2', m2_uuid, '1.9', 'Name of module m2',
                '2013-10-01 12:24:00.000000+02', 9, 1),
            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 21:43:00.000000+02', 5, 1),
            ('Collection', 'c1', c1_uuid, '1.6', 'Name of collection c1',
                '2013-10-03 12:00:00.000000+02', 6, 1),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[2]),
            (module_idents[2], module_idents[0]),
            (module_idents[2], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[3]),
            (module_idents[3], module_idents[0]),
            (module_idents[3], module_idents[1])))

        from ..database import create_collection_minor_versions
        create_collection_minor_versions(cursor, module_idents[2])
        create_collection_minor_versions(cursor, module_idents[3])

        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        self.assertEqual(old_num_modules + 4, new_num_modules)

    @db_connect
    def test_create_minor_versions(self, cursor):
        """Test case for when there are modules published in between collection
        versions and there is a need to create minor versions of a collection
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        m1_uuid = str(uuid.uuid4())
        m2_uuid = str(uuid.uuid4())
        c1_uuid = str(uuid.uuid4())
        module_idents = list(self.insert_modules(cursor, (
            # portal_type, moduleid, uuid, version, name, revised,
            # major_version, minor_version
            ('Module', 'm1', m1_uuid, '1.1', 'Name of module m1',
                '2013-10-01 11:24:00.000000-07', 1, 1),
            ('Module', 'm2', m2_uuid, '1.9', 'Name of module m2',
                '2013-10-01 12:24:00.000000-07', 9, 1),
            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 21:43:00.000000-07', 5, 1),
            ('Module', 'm1', m1_uuid, '1.2', 'Changed name of module m1',
                '2013-10-03 09:00:00.000000-07', 2, 1),
            ('Collection', 'c1', c1_uuid, '1.6', 'Name of collection c1',
                '2013-10-03 12:00:00.000000-07', 6, 1),
            ('Module', 'm1', m1_uuid, '1.3', 'Changed name again m1',
                '2013-10-03 12:01:00.000000-07', 3, 1),
            ('Module', 'm2', m2_uuid, '1.10', 'Changed name of module m2',
                '2013-10-03 12:02:00.000000-07', 10, 1),
            ('Module', 'm2', m2_uuid, '1.11', 'Changed name of module m2',
                '2013-10-03 12:03:00.000000-07', 11, 1),
            ('Collection', 'c1', c1_uuid, '1.7', 'Name of collection c1',
                '2013-10-07 12:00:00.000000-07', 7, 1),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[2]),
            (module_idents[2], module_idents[0]),
            (module_idents[2], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[4]),
            (module_idents[4], module_idents[3]),
            (module_idents[4], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[7]),
            (module_idents[7], module_idents[5]),
            (module_idents[7], module_idents[6])))

        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        # we inserted 9 rows into the modules table
        self.assertEqual(old_num_modules + 9, new_num_modules)

        from ..database import create_collection_minor_versions
        create_collection_minor_versions(cursor, module_idents[2])
        create_collection_minor_versions(cursor, module_idents[4])

        old_num_modules = new_num_modules
        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        # we should have inserted 4 minor versions for c1: 5.2, 6.2, 6.3, 6.4
        self.assertEqual(old_num_modules + 4, new_num_modules)

        tree_sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr
            WHERE tr.documentid = %s
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON c.parent_id = t.node
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t'''

        # Check c1 v5.2
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 5, 2])
        rev_5_2 = cursor.fetchone()
        # revised
        self.assertEqual(str(rev_5_2[7]), '2013-10-03 09:00:00-07:00')

        # Check tree contains m1 v1.2 and m2 v1.9
        cursor.execute(tree_sql, [rev_5_2[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 3)
        self.assertEqual(tree[0][2], rev_5_2[0])
        self.assertEqual(tree[1][2], module_idents[3])
        self.assertEqual(tree[2][2], module_idents[1])

        # Check c1 v6.2
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 2])
        rev_6_2 = cursor.fetchone()
        # revised
        self.assertEqual(str(rev_6_2[7]), '2013-10-03 12:01:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.9
        cursor.execute(tree_sql, [rev_6_2[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 3)
        self.assertEqual(tree[0][2], rev_6_2[0])
        self.assertEqual(tree[1][2], module_idents[5])
        self.assertEqual(tree[2][2], module_idents[1])

        # Check c1 v6.3
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 3])
        rev_6_3 = cursor.fetchone()
        # revised
        self.assertEqual(str(rev_6_3[7]), '2013-10-03 12:02:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.10
        cursor.execute(tree_sql, [rev_6_3[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 3)
        self.assertEqual(tree[0][2], rev_6_3[0])
        self.assertEqual(tree[1][2], module_idents[5])
        self.assertEqual(tree[2][2], module_idents[6])

        # Check c1 v6.4
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 4])
        rev_6_4 = cursor.fetchone()
        # revised
        self.assertEqual(str(rev_6_4[7]), '2013-10-03 12:03:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.11
        cursor.execute(tree_sql, [rev_6_4[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 3)
        self.assertEqual(tree[0][2], rev_6_4[0])
        self.assertEqual(tree[1][2], module_idents[5])
        self.assertEqual(tree[2][2], module_idents[7])
