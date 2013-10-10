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

from cnxupgrade.upgrades.to_html import (
        get_module_uuid, produce_html_for_module)


CONNECTION_SETTINGS_KEY = 'db-connection-string'

here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
DB_SCHEMA_FILE_PATHS = (
    os.path.join(DB_SCHEMA_DIRECTORY, 'schema.sql'),
    os.path.join(DB_SCHEMA_DIRECTORY, 'trees.sql'),
    # Module fulltext indexing
    os.path.join(DB_SCHEMA_DIRECTORY, 'fulltext-indexing.sql'),
    # cnx-user user shadow table.
    os.path.join(DB_SCHEMA_DIRECTORY, 'cnx-user.schema.sql'),
    # Functions
    os.path.join(DB_SCHEMA_DIRECTORY, 'shred_collxml.sql'),
    os.path.join(DB_SCHEMA_DIRECTORY, 'tree_to_json.sql'),
    )


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
    'update-buylink': _read_sql_file('update-buylink'),
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

def get_current_module_ident(moduleid, cursor):
    sql = '''SELECT m.module_ident FROM modules m 
        WHERE m.moduleid = %s ORDER BY module_ident DESC'''
    cursor.execute(sql, [moduleid])
    results = cursor.fetchone()[0]
    return results

def get_minor_version(module_ident, cursor):
    sql = '''SELECT m.minor_version
            FROM modules m WHERE m.module_ident = %s'''
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
    INSERT INTO modules (portal_type, moduleid, uuid, name, created, revised,
        abstractid,licenseid,doctype,submitter,submitlog,stateid,parent,language,
        authors,maintainers,licensors,parentauthors,google_analytics,buylink,
        major_version, minor_version)
        SELECT m.portal_type, m.moduleid, m.uuid, m.name, m.created, {},
        m.abstractid, m.licenseid, m.doctype, m.submitter, m.submitlog, m.stateid, m.parent,
        m.language, m.authors, m.maintainers, m.licensors, m.parentauthors,
        m.google_analytics, m.buylink, m.major_version, {}
        FROM modules m
        WHERE m.module_ident = {}
    RETURNING module_ident
    '''
    if revised is None:
        sql = sql.format('CURRENT_TIMESTAMP', '%s', '%s')
        params = [next_minor_version, collection_ident]
    else:
        sql = sql.format('%s', '%s', '%s')
        params = [revised, next_minor_version, collection_ident]
    cursor.execute(sql, params)
    results = cursor.fetchone()[0]
    return results

def republish_module(plpy, td):
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

    portal_type = td['new']['portal_type']
    
    modified='OK'

    plpy.log('Trigger fired on %s' % (td['new']['moduleid'],))

    with plpydbapi.connect() as db_connection:
        with db_connection.cursor() as cursor:

            current_module_ident = get_current_module_ident(td['new']['moduleid'], cursor=cursor)
            if current_module_ident:
                # need to overide autogen uuid to keep it constant per moduleid
                uuid = get_module_uuid(db_connection, td['new']['moduleid'])
                td['new']['uuid'] = uuid
                modified = 'MODIFY'
            else:
                # nothing to do if the module/collection is new
                return modified

            if portal_type != 'Module':
                # nothing else to do if something else is being published
                return modified

            # Module is republished
            for collection_id in get_collections(current_module_ident, cursor=cursor):
                minor = next_version(collection_id, cursor=cursor)
                new_ident = republish_collection(minor, collection_id, cursor=cursor)
                rebuild_collection_tree(collection_id, {
                    collection_id: new_ident,
                    current_module_ident: td['new']['module_ident'],
                    }, cursor=cursor)
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
                message = produce_html_for_module(db_connection, cursor, td['new']['module_ident'])
                if message:
                    plpy.error(message)
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

def create_collection_minor_versions(cursor, collection_ident):
    """Migration to create collection minor versions from the existing modules
    and collections """
    # Get the collection tree
    # modules = []
    # Loop over each module
    #    If there is a version of the modules that have next_collection.revised > revised > collection.revised 
    #        modules.append((module_ident, revised))
    # sort modules by revised ascending
    # for each module in modules
    #    increment minor version of collection, with module's revised time
    #    rebuild collection tree

    # fetches the collection version of interest and the next version
    # and in case the collection version of interest is latest, revised for the
    # next version is now
    cursor.execute('''
    (
        WITH current AS (
            SELECT uuid, revised FROM modules WHERE module_ident = %s
        )
        SELECT m.module_ident, m.revised FROM modules m, current
        WHERE m.uuid = current.uuid AND m.revised >= current.revised
        ORDER BY m.revised
    )
    UNION ALL SELECT NULL, CURRENT_TIMESTAMP
    LIMIT 2;
    ''',
        [collection_ident])
    results = cursor.fetchall()
    this_module_ident, this_revised = results[0]
    next_module_ident, next_revised = results[1]

    # gather all relevant module versions
    sql = '''SELECT DISTINCT(m.module_ident), m.revised FROM modules m
    WHERE m.revised > %s AND m.revised < %s AND m.uuid = (
        SELECT uuid FROM modules WHERE module_ident = %s)
    ORDER BY m.revised
    '''

    old_module_idents = {}
    modules = []
    for module_ident, portal_type in get_collection_tree(collection_ident,
            cursor):
        if portal_type == 'Module':
            cursor.execute(sql, [this_revised, next_revised, module_ident])

            # get all the modules with the same uuid that have been published
            # between this collection version and the next version
            results = cursor.fetchall()

            # about what the loop below does...
            #
            # e.g. we have a module m1, and it was updated 3 times between the
            # time the collection is updated
            #
            # let's say the module_ident for current m1 is 1 and the updated
            # versions 3, 6, 9
            #
            # then results looks like [(3, revised), (6, revised), (9, revised)
            #
            # we need to know that 3 replaces 1, 6 replaces 3 and 9 replaces 6
            # so that we know what to change when we copy the collection tree
            #
            # so old_module_idents should have:
            # {3: 1, 6: 3, 9: 6}
            for i, data in enumerate(results):
                if i == 0:
                    old_module_idents[data[0]] = module_ident
                else:
                    old_module_idents[data[0]] = results[i - 1][0]
                modules.append(data)

    modules.sort(lambda a, b: cmp(a[1], b[1])) # sort modules by revised

    next_minor_version = next_version(collection_ident, cursor=cursor)
    for module_ident, module_revised in modules:
        new_ident = republish_collection(next_minor_version, collection_ident, cursor=cursor, revised=module_revised)
        rebuild_collection_tree(collection_ident, {
            collection_ident: new_ident,
            old_module_idents[module_ident]: module_ident,
            }, cursor=cursor)

        next_minor_version += 1
        collection_ident = new_ident
