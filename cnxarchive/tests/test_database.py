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
