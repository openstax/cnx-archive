# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database models and utilities"""
import os
import psycopg2


CONNECTION_SETTINGS_KEY = 'db-connection-string'

here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
DB_SCHEMA_FILE_PATHS = (
    os.path.join(DB_SCHEMA_DIRECTORY, 'schema.sql'),
    os.path.join(DB_SCHEMA_DIRECTORY, 'trees.sql'),
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


def republish_module(plpy, td):
    """Postgres database trigger for republishing a module

    When a module is republished, the versions of the collections that it is
    part of will need to be updated (a minor update).  The cnxml will need to
    be transformed to html.

    When a collection is republished, the version needs to be updated (a major
    update).
    """
    from xml.etree import ElementTree

    import plpydbapi

    import cnxupgrade.upgrades.to_html

    conn = plpydbapi.connect()
    cursor = conn.cursor()
    portal_type = td['new']['portal_type']

    def get_current_module_ident(moduleid):
        stmt = plpy.prepare('SELECT m.module_ident FROM modules m '
                'WHERE m.moduleid = $1 ORDER BY created DESC', ['text'])
        results = plpy.execute(stmt, [moduleid])
        if results:
            return results[0]['module_ident']

    def get_version(module_ident):
        stmt = plpy.prepare('SELECT m.version FROM modules m '
                'WHERE m.module_ident = $1', ['integer'])
        return plpy.execute(stmt, [module_ident])[0]['version']

    def next_version(module_ident, release):
        # "major" release bumps the first number so 1.4 becomes 2.1
        # "minor" release bumps the number after the dot so 1.4 becomes 1.5
        current_version = get_version(module_ident)
        major, minor = current_version.split('.', 1)
        if release == 'major':
            return '{}.1'.format(int(major) + 1)
        return '{}.{}'.format(major, int(minor) + 1)

    def get_collections(module_ident):
        """Get all the collections that the module is part of
        """
        sql = '''
        WITH RECURSIVE t(node, parent, path, document) AS (
            SELECT tr.nodeid, tr.parent_id, ARRAY[tr.nodeid], tr.documentid
            FROM trees tr
            WHERE tr.documentid = $1
        UNION ALL
            SELECT c.nodeid, c.parent_id, path || ARRAY[c.nodeid], c.documentid
            FROM trees c JOIN t ON (c.nodeid = t.parent)
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT m.module_ident
        FROM t JOIN modules m ON (t.document = m.module_ident)
        WHERE t.parent IS NULL
        '''
        stmt = plpy.prepare(sql, ['integer'])
        for i in plpy.execute(stmt, [module_ident]):
            yield i['module_ident']

    def rebuild_collection_tree(old_collection_ident, new_document_id_map):
        """Create a new tree for the collection based on the old tree but with
        new document ids
        """
        sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr WHERE tr.documentid = $1
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON (c.nodeid = t.parent OR c.parent_id = t.node)
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t
        '''
        stmt = plpy.prepare(sql, ['integer'])
        tree = {} # { old_nodeid: {'data': ...}, ...}
        children = {} # { nodeid: [child_nodeid, ...], child_nodeid: [...]}
        for i in plpy.execute(stmt, [old_collection_ident]):
            tree[i['node']] = {'data': i, 'new_nodeid': None}
            children.setdefault(i['parent'], [])
            children[i['parent']].append(i['node'])

        sql = '''
        INSERT INTO trees
        VALUES (DEFAULT, $1, $2, $3, $4, $5)
        RETURNING nodeid
        '''
        stmt = plpy.prepare(sql, ['integer', 'integer', 'text', 'integer',
            'boolean'])
        root_node = children[None][0]
        def build_tree(node, parent):
            data = tree[node]['data']
            new_node = plpy.execute(stmt, [parent,
                new_document_id_map.get(data['document'], data['document']),
                data['title'], data['childorder'],
                data['latest']])[0]['nodeid']
            for i in children.get(node, []):
                build_tree(i, new_node)
        build_tree(root_node, None)

    def update_versions_in_file(fileid, new_collection_version):
        new_moduleid = td['new']['moduleid']
        new_module_version = td['new']['version']

        stmt = plpy.prepare('SELECT file FROM files WHERE fileid = $1',
                ['integer'])
        xmlfile = plpy.execute(stmt, [fileid])[0]['file']
        namespace = {
                'md': 'http://cnx.rice.edu/mdml',
                'col': 'http://cnx.rice.edu/collxml',
                }
        etree = ElementTree.fromstring(xmlfile)

        url = etree.find('.//md:content-url', namespace).text
        # url should look like "http://cnx.org/content/col11406/1.7
        # strip the old version out of the url and add the new version
        url = '{}/{}'.format(url.rsplit('/', 1)[0], new_collection_version)
        etree.find('.//md:content-url', namespace).text = url

        etree.find('.//md:version', namespace).text = new_collection_version

        module_attribute = '{http://cnx.rice.edu/system-info}version-at-this-collection-version'
        for m in etree.findall(
                './/col:module[document="{}"]'.format(new_moduleid), namespace):
            m.set(module_attribute, new_module_version)

        stmt = plpy.prepare('INSERT INTO files (file) VALUES ($1) '
                'RETURNING fileid', ['bytea'])
        return plpy.execute(stmt, [ElementTree.tostring(etree)])[0]['fileid']

    def copy_collection_files(old_ident, new_ident, new_version):
        stmt = plpy.prepare('''
        SELECT m.fileid
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = $1 AND m.filename = 'collection.xml'
        ''', ['integer'])

        copy_module_file_stmt = plpy.prepare('''
        INSERT INTO module_files
            (module_ident, fileid, filename, mimetype)
            SELECT $1, $2, filename, mimetype FROM module_files
            WHERE module_ident = $3
        RETURNING module_ident
        ''', ['integer', 'integer', 'integer'])

        plpy.warning(list(plpy.execute(plpy.prepare('SELECT documentid FROM trees WHERE parent_id IS NULL'))))

        for result in plpy.execute(stmt, [old_ident]):
            new_fileid = update_versions_in_file(result['fileid'], new_version)
            plpy.execute(copy_module_file_stmt, [new_ident, new_fileid, old_ident])

    def republish_collection(next_version, collection_ident):
        """Insert a new row for collection_ident with a new version and return
        the module_ident of the row inserted
        """
        sql = '''
        INSERT INTO modules
            SELECT NEXTVAL('modules_module_ident_seq'), m.portal_type, m.moduleid,
            m.uuid, $1, m.name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, m.abstractid,
            m.licenseid, m.doctype, m.submitter, m.submitlog, m.stateid, m.parent,
            m.language, m.authors, m.maintainers, m.licensors, m.parentauthors,
            m.google_analytics, m.buylink
            FROM modules m
            WHERE m.module_ident = $2
        RETURNING module_ident
        '''
        stmt = plpy.prepare(sql, ['text', 'integer'])
        results = plpy.execute(stmt, [next_version, collection_ident])
        return results[0]['module_ident']

    current_module_ident = get_current_module_ident(td['new']['moduleid'])
    if not current_module_ident:
        # nothing to do if the module/collection is new
        return

    if portal_type != 'Module':
        # nothing to do if something else is being published
        return

    # Module is republished

    # generate html from cnxml
    # TODO: module files not created yet at the time of this trigger because
    # module files require a valid module_ident
    #cnxupgrade.upgrades.to_html.produce_html_for_module(
    #        conn, cursor, td['new']['module_ident'])

    for collection_id in get_collections(current_module_ident):
        new_version = next_version(collection_id, 'minor')
        new_ident = republish_collection(new_version, collection_id)
        rebuild_collection_tree(collection_id, {
            collection_id: new_ident,
            current_module_ident: td['new']['module_ident'],
            })
        # No need to copy collection.xml
#        copy_collection_files(collection_id, new_ident, new_version)
