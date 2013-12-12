# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database models and utilities"""
import datetime
import os
import psycopg2
import re

from .to_html import produce_html_for_module


CONNECTION_SETTINGS_KEY = 'db-connection-string'

here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
DB_SCHEMA_FILES = (
    'schema.sql',
    # Collection trees
    'trees.sql',
    # Module fulltext indexing
    'fulltext-indexing.sql',
    # cnx-user user shadow table.
    'cnx-user.schema.sql',
    # Functions for collections
    'shred_collxml.sql',
    'tree_to_json.sql',
    'common-functions.sql',
    'hits-functions.sql',
    )

DB_SCHEMA_FILE_PATHS = tuple([os.path.join(DB_SCHEMA_DIRECTORY, dsf)
                              for dsf in  DB_SCHEMA_FILES])

def _read_sql_file(name):
    path = os.path.join(SQL_DIRECTORY, '{}.sql'.format(name))
    with open(path, 'r') as fp:
        return fp.read()
SQL = {
    'get-module': _read_sql_file('get-module'),
    'get-module-metadata': _read_sql_file('get-module-metadata'),
    'get-resource': _read_sql_file('get-resource'),
    'get-resource-by-filename': _read_sql_file('get-resource-by-filename'),
    'get-tree-by-uuid-n-version': _read_sql_file('get-tree-by-uuid-n-version'),
    'get-module-versions': _read_sql_file('get-module-versions'),
    'get-subject-list': _read_sql_file('get-subject-list'),
    }


def initdb(settings):
    """Initialize the database from the given settings.
    If settings is None, the settings will be looked up via pyramid.
    """
    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            for schema_filepath in DB_SCHEMA_FILE_PATHS:
                with open(schema_filepath, 'r') as f:
                    cursor.execute(f.read())
            sql_constants = [os.path.join(DB_SCHEMA_DIRECTORY, filename)
                             for filename in os.listdir(DB_SCHEMA_DIRECTORY)
                             if filename.startswith('constant-')]
            for filepath in sql_constants:
                with open(filepath, 'r') as f:
                    cursor.execute(f.read())


def get_module_uuid(db_connection, moduleid):
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT uuid FROM modules WHERE moduleid = %s;",
                       (moduleid,))
        uuid = None
        result = cursor.fetchone()
        if result:
            uuid=result[0]
    return uuid

def get_current_module_ident(moduleid, cursor):
    sql = '''SELECT m.module_ident FROM modules m
        WHERE m.moduleid = %s ORDER BY revised DESC'''
    cursor.execute(sql, [moduleid])
    results = cursor.fetchone()
    if results:
        return results[0]

def get_minor_version(module_ident, cursor):
    sql = '''SELECT m.minor_version
            FROM modules m 
            WHERE m.module_ident = %s
            ORDER BY m.revised DESC'''
    cursor.execute(sql, [module_ident])
    results = cursor.fetchone()[0]
    return results

def next_version(module_ident, cursor):
    minor = get_minor_version(module_ident, cursor)
    return minor + 1

def get_collections(module_ident, cursor):
    """Get all the collections that the module is part of
    """
    sql = '''
    WITH RECURSIVE t(node, parent, path, document) AS (
        SELECT tr.nodeid, tr.parent_id, ARRAY[tr.nodeid], tr.documentid
        FROM trees tr
        WHERE tr.documentid = %s
    UNION ALL
        SELECT c.nodeid, c.parent_id, path || ARRAY[c.nodeid], c.documentid
        FROM trees c JOIN t ON (c.nodeid = t.parent)
        WHERE not c.nodeid = ANY(t.path)
    )
    SELECT m.module_ident
    FROM t JOIN latest_modules m ON (t.document = m.module_ident)
    WHERE t.parent IS NULL
    '''
    cursor.execute(sql, [module_ident])
    for i in cursor.fetchall():
        yield i[0]

def rebuild_collection_tree(old_collection_ident, new_document_id_map, cursor):
    """Create a new tree for the collection based on the old tree but with
    new document ids
    """
    sql = '''
    WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
        SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr WHERE tr.documentid = %s
    UNION ALL
        SELECT c.*, path || ARRAY[c.nodeid]
        FROM trees c JOIN t ON (c.parent_id = t.node)
        WHERE not c.nodeid = ANY(t.path)
    )
    SELECT * FROM t
    '''

    def get_tree():
        cursor.execute(sql, [old_collection_ident])
        for i in cursor.fetchall():
            yield dict(zip(('node', 'parent', 'document', 'title',
                'childorder', 'latest', 'path'), i))

    tree = {} # { old_nodeid: {'data': ...}, ...}
    children = {} # { nodeid: [child_nodeid, ...], child_nodeid: [...]}
    for i in get_tree():
        tree[i['node']] = {'data': i, 'new_nodeid': None}
        children.setdefault(i['parent'], [])
        children[i['parent']].append(i['node'])

    sql = '''
    INSERT INTO trees (nodeid, parent_id, documentid, title, childorder, latest)
    VALUES (DEFAULT, %s, %s, %s, %s, %s)
    RETURNING nodeid
    '''

    def execute(fields):
        cursor.execute(sql, fields)
        results = cursor.fetchone()[0]
        return results

    root_node = children[None][0]
    def build_tree(node, parent):
        data = tree[node]['data']
        new_node = execute([parent, new_document_id_map.get(data['document'],
            data['document']), data['title'], data['childorder'],
            data['latest']])
        for i in children.get(node, []):
            build_tree(i, new_node)
    build_tree(root_node, None)

def republish_collection(next_minor_version, collection_ident, cursor,
        revised=None):
    """Insert a new row for collection_ident with a new version and return
    the module_ident of the row inserted
    """
    sql = '''
    INSERT INTO modules (portal_type, moduleid, uuid, version, name, created, revised,
        abstractid,licenseid,doctype,submitter,submitlog,stateid,parent,language,
        authors,maintainers,licensors,parentauthors,google_analytics,buylink,
        major_version, minor_version)
        SELECT m.portal_type, m.moduleid, m.uuid, m.version, m.name, m.created, {},
        m.abstractid, m.licenseid, m.doctype, m.submitter, m.submitlog, m.stateid, m.parent,
        m.language, m.authors, m.maintainers, m.licensors, m.parentauthors,
        m.google_analytics, m.buylink, m.major_version, %s
        FROM modules m
        WHERE m.module_ident = %s
    RETURNING module_ident
    '''
    if revised is None:
        sql = sql.format('CURRENT_TIMESTAMP')
        params = [next_minor_version, collection_ident]
    else:
        sql = sql.format('%s')
        params = [revised, next_minor_version, collection_ident]
    cursor.execute(sql, params)
    results = cursor.fetchone()[0]
    return results

def set_version(portal_type, legacy_version, td):
    """Sets the major_version and minor_version if they are not set
    """
    major = td['new']['major_version']
    minor = td['new']['minor_version']
    modified = 'OK'
    legacy_major, legacy_minor = legacy_version.split('.')

    if portal_type == 'Collection':
        # For collections, both major and minor needs to be set
        modified = 'MODIFY'
        td['new']['major_version'] = int(legacy_minor)
        if td['new']['minor_version'] is None:
            td['new']['minor_version'] = 1

    elif portal_type == 'Module':
        # For modules, major should be set and minor should be None
        modified = 'MODIFY'
        td['new']['major_version'] = int(legacy_minor)
        td['new']['minor_version'] = None

    return modified

def republish_module(td, cursor, db_connection):
    """When a module is republished, the versions of the collections that it is
    part of will need to be updated (a minor update).


    e.g. there is a collection c1 v2.1, which contains module m1 v3

    m1 is updated, we have a new row in the modules table with m1 v4

    this trigger will create increment the minor version of c1, so we'll have
    c1 v2.2

    we need to create a collection tree for c1 v2.2 which is exactly the same
    as c1 v2.1, but with m1 v4 instead of m1 v3, and c1 v2.2 instead of c1 v2.2
    """
    portal_type = td['new']['portal_type']
    modified = 'OK'
    moduleid = td['new']['moduleid']
    legacy_version = td['new']['version']

    modified = set_version(portal_type, legacy_version, td)

    current_module_ident = get_current_module_ident(moduleid, cursor)
    if current_module_ident:
        # need to overide autogen uuid to keep it constant per moduleid
        uuid = get_module_uuid(db_connection, moduleid)
        td['new']['uuid'] = uuid
        modified = 'MODIFY'
    else:
        # nothing to do if the module/collection is new
        return modified

    if portal_type != 'Module':
        # nothing else to do if something else is being published
        return modified

    # Module is republished
    for collection_id in get_collections(current_module_ident, cursor):
        minor = next_version(collection_id, cursor)
        new_ident = republish_collection(minor, collection_id, cursor)
        rebuild_collection_tree(collection_id, {
            collection_id: new_ident,
            current_module_ident: td['new']['module_ident'],
            }, cursor)

    return modified

def republish_module_trigger(plpy, td):
    """Postgres database trigger for republishing a module

    When a module is republished, the versions of the collections that it is
    part of will need to be updated (a minor update).


    e.g. there is a collection c1 v2.1, which contains module m1 v3

    m1 is updated, we have a new row in the modules table with m1 v4

    this trigger will create increment the minor version of c1, so we'll have
    c1 v2.2

    we need to create a collection tree for c1 v2.2 which is exactly the same
    as c1 v2.1, but with m1 v4 instead of m1 v3, and c1 v2.2 instead of c1 v2.2
    """
    import plpydbapi

    plpy.log('Trigger fired on %s' % (td['new']['moduleid'],))

    with plpydbapi.connect() as db_connection:
        with db_connection.cursor() as cursor:
            modified = republish_module(td, cursor, db_connection)
        db_connection.commit()

    return modified


def add_module_file(plpy, td):
    """Postgres database trigger for adding a module file

    When a module file index.cnxml is added to the database, the trigger
    transforms it into html and stores it in the database as index.html.
    """
    import plpydbapi

    filename = td['new']['filename']
    if filename != 'index.cnxml':
        return

    stmt = plpy.prepare('''SELECT * FROM module_files
    WHERE filename = 'index.html' AND module_ident = $1''', ['integer'])
    results = plpy.execute(stmt, [td['new']['module_ident']])

    if len(results) == 0:
        with plpydbapi.connect() as db_connection:
            with db_connection.cursor() as cursor:
                produce_html_for_module(db_connection, cursor, td['new']['module_ident'])
            db_connection.commit()
    return

def get_collection_tree(collection_ident, cursor):
    cursor.execute('''
    WITH RECURSIVE t(node, parent, document, path) AS (
        SELECT tr.nodeid, tr.parent_id, tr.documentid, ARRAY[tr.nodeid]
        FROM trees tr
        WHERE tr.documentid = %s
    UNION ALL
        SELECT c.nodeid, c.parent_id, c.documentid, path || ARRAY[c.nodeid]
        FROM trees c JOIN t ON c.parent_id = t.node
        WHERE NOT c.nodeid = ANY(t.path)
    )
    SELECT t.document, m.portal_type
    from t JOIN modules m ON t.document = m.module_ident''', [collection_ident])
    for i in cursor.fetchall():
        yield i
