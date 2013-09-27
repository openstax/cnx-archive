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
        INSERT INTO trees (nodeid, parent_id, documentid, title, childorder, latest)
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

    def republish_collection(next_version, collection_ident):
        """Insert a new row for collection_ident with a new version and return
        the module_ident of the row inserted
        """
        sql = '''
        INSERT INTO modules (portal_type, moduleid, uuid, version, name, created, revised,
            abstractid,licenseid,doctype,submitter,submitlog,stateid,parent,language,
            authors,maintainers,licensors,parentauthors,google_analytics,buylink)
            SELECT m.portal_type, m.moduleid, m.uuid, $1, m.name, m.created, CURRENT_TIMESTAMP,
            m.abstractid, m.licenseid, m.doctype, m.submitter, m.submitlog, m.stateid, m.parent,
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
    for collection_id in get_collections(current_module_ident):
        new_version = next_version(collection_id, 'minor')
        new_ident = republish_collection(new_version, collection_id)
        rebuild_collection_tree(collection_id, {
            collection_id: new_ident,
            current_module_ident: td['new']['module_ident'],
            })


class ResourceNotFoundException(Exception):
    """Raised when a resource file is not found in the database
    """


def add_module_file(plpy, td):
    """Postgres database trigger for adding a module file

    When a module file index.cnxml is added to the database, the trigger
    transforms it into html and stores it in the database as index.html.
    """
    import json
    import re

    from cnxupgrade.upgrades.to_html import (
            transform_cnxml_to_html, BytesIO, SQL_RESOURCE_INFO_STATEMENT,
            etree, _split_ref, SQL_MODULE_BY_ID_N_VERSION_STATEMENT)

    def to_plpy_stmt(dbapi_stmt):
        """Change a statment like "SELECT * FROM a WHERE id = %s" to
        "SELECT * FROM a WHERE id = $1"
        """
        def f(matchobj, arg=[0]):
            arg[0] += 1
            return '${}'.format(arg[0])
        return re.sub('%s', f, dbapi_stmt)

    # Copied from cnxupgrade.upgrades.to_html, modified to work with plpy
    def fix_reference_urls(document_ident, html):
        """Fix the document's internal references to other documents and
        resources.

        The database connection, passed as ``db_connection`` is used to lookup
        resources by both filename and the given ``document_ident``, which is
        the document's 'module_ident' value.

        Returns a modified version of the html document.
        """
        xml = etree.parse(html)
        xml_doc = xml.getroot()

        def get_resource_info(filename):
            stmt = plpy.prepare(to_plpy_stmt(SQL_RESOURCE_INFO_STATEMENT),
                    ['integer', 'text'])
            results = plpy.execute(stmt, [document_ident, filename])
            try:
                info = results[0]['row_to_json']
            except:
                raise ResourceNotFoundException
            return json.loads(info)

        def get_module_uuid(module, version):
            stmt = plpy.prepare(to_plpy_stmt(
                SQL_MODULE_BY_ID_N_VERSION_STATEMENT), ['text', 'text'])
            results = plpy.execute(stmt, [module, version])
            uuid = results[0]['uuid']
            return uuid

        # Namespace reworking...
        namespaces = xml_doc.nsmap.copy()
        namespaces['html'] = namespaces.pop(None)

        # Fix references to resources.
        for img in xml_doc.xpath('//html:img', namespaces=namespaces):
            filename = img.get('src')
            info = get_resource_info(filename)
            img.set('src', '/resources/{}/{}'.format(info['hash'], filename))

        # Fix references to documents.
        for anchor in xml_doc.xpath('//html:a', namespaces=namespaces):
            ref = anchor.get('href')
            if (ref.startswith('#') or ref.startswith('http')) \
               and not ref.startswith('/'):
                continue
            id, version = _split_ref(ref)
            # FIXME We need a better way to determine if the link is a
            #       module or resource reference. Probably some way to
            #       add an attribute in the xsl.
            #       The try & except can be removed after we fix this.
            try:
                uuid = get_module_uuid(id, version)
            except TypeError:
                continue
            anchor.set('href', '/contents/{}@{}'.format(uuid, version))

        return etree.tostring(xml_doc)

    # Copied from cnxupgrade.upgrades.to_html, modified to work with plpy
    def produce_html_for_module(ident):
        message = None
        # FIXME There is a better way to join this information, but
        #       for the sake of testing scope stick with the simple yet
        #       redundant lookups.
        stmt = plpy.prepare("SELECT filename, fileid FROM module_files "
                       "  WHERE module_ident = $1;", ['integer'])
        results = plpy.execute(stmt, (ident,))
        file_metadata = dict([(r['filename'], r['fileid']) for r in results])
        file_id = file_metadata['index.cnxml']
        # Grab the file for transformation.
        stmt = plpy.prepare("SELECT file FROM files WHERE fileid = $1;",
                ['integer'])
        results = plpy.execute(stmt, (file_id,))
        cnxml = results[0]['file']
        cnxml = cnxml[:]
        try:
            index_html = transform_cnxml_to_html(cnxml)
            # Fix up content references to cnx-archive specific urls.
            index_html = fix_reference_urls(ident, BytesIO(index_html))
        except ResourceNotFoundException:
            # if a resource file is not in the database yet, wait for the next
            # insert
            return False
        except Exception as exc:
            # TODO Log the exception in more detail.
            message = exc.message
            raise
        else:
            # Insert the collection.html into the database.
            stmt = plpy.prepare("INSERT INTO files (file) VALUES ($1) "
                           "RETURNING fileid;", ['bytea'])
            results = plpy.execute(stmt, [index_html])
            html_file_id = results[0]['fileid']
            stmt = plpy.prepare("INSERT INTO module_files "
                           "  (module_ident, fileid, filename, mimetype) "
                           "  VALUES ($1, $2, $3, $4);",
                           ['integer', 'integer', 'text', 'text'])
            plpy.execute(stmt, [ident, html_file_id, 'index.html',
                'text/html'])
        return message

    filename = td['new']['filename']
    if filename != 'index.cnxml':
        return

    stmt = plpy.prepare('''SELECT * FROM module_files
    WHERE filename = 'index.html' AND module_ident = $1''', ['integer'])
    results = plpy.execute(stmt, [td['new']['module_ident']])

    if len(results) == 0: 
        message = produce_html_for_module(td['new']['module_ident'])
        if message:
            plpy.error(message)
    return
