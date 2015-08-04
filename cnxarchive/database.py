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

from . import config
from .transforms import (
    produce_cnxml_for_module, produce_html_for_module,
    transform_abstract_to_cnxml, transform_abstract_to_html,
    )
from .utils import split_ident_hash


here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
DB_SCHEMA_FILES = (
    'schema.sql',
    # Collection trees
    'trees.sql',
    # Module fulltext indexing
    'fulltext-indexing.sql',
    # Functions for collections
    'shred_collxml.sql',
    'tree_to_json.sql',
    'common-functions.sql',
    'hits-functions.sql',
    )
DB_SCHEMA_FILE_PATHS = tuple([os.path.join(DB_SCHEMA_DIRECTORY, dsf)
                              for dsf in DB_SCHEMA_FILES])


def _read_sql_file(name):
    path = os.path.join(SQL_DIRECTORY, '{}.sql'.format(name))
    with open(path, 'r') as fp:
        return fp.read()


SQL = {
    'get-module': _read_sql_file('get-module'),
    'get-content-from-legacy-id': _read_sql_file('get-content-from-legacy-id'),
    'get-content-from-legacy-id-ver': _read_sql_file('get-content-from-legacy-id-ver'),
    'get-module-metadata': _read_sql_file('get-module-metadata'),
    'get-resource': _read_sql_file('get-resource'),
    'get-resource-by-filename': _read_sql_file('get-resource-by-filename'),
    'get-resourceid-by-filename': _read_sql_file('get-resourceid-by-filename'),
    'get-tree-by-uuid-n-version': _read_sql_file('get-tree-by-uuid-n-version'),
    'get-module-versions': _read_sql_file('get-module-versions'),
    'get-subject-list': _read_sql_file('get-subject-list'),
    'get-featured-links': _read_sql_file('get-featured-links'),
    'get-users-by-ids': _read_sql_file('get-users-by-ids'),
    'get-service-state-messages': _read_sql_file('get-service-state-messages'),
    'get-license-info-as-json': _read_sql_file('get-license-info-as-json'),
    }


def initdb(settings):
    """Initialize the database from the given settings."""
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
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


def get_module_ident_from_ident_hash(ident_hash, cursor):
    """Returns the moduleid for a given ``ident_hash``."""
    uuid, (mj_ver, mn_ver) = split_ident_hash(ident_hash, split_version=True)
    args = [uuid]
    stmt = "SELECT module_ident FROM {} WHERE uuid = %s"
    table_name = 'modules'
    if mj_ver is None:
        table_name = 'latest_modules'
    else:
        args.append(mj_ver)
        stmt += " AND major_version = %s"
    if mn_ver is not None:
        args.append(mn_ver)
        stmt += " AND minor_version = %s"
    stmt = stmt.format(table_name)

    cursor.execute(stmt, args)
    try:
        module_ident = cursor.fetchone()[0]
    except TypeError:  # NoneType
        module_ident = None
    return module_ident


def get_tree(ident_hash, cursor):
    """Given an ``ident_hash``, return a JSON representation
    of the binder tree.
    """
    uuid, version = split_ident_hash(ident_hash)
    cursor.execute(SQL['get-tree-by-uuid-n-version'],
                   (uuid, version,))
    try:
        tree = cursor.fetchone()[0]
    except TypeError:  # NoneType
        raise ContentNotFound()
    if type(tree) in (type(''),type(u'')):
        import json
        return json.loads(tree)
    else:
        return tree


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
    new_ident = cursor.fetchone()[0]
    cursor.execute("""\
        INSERT INTO modulekeywords (module_ident, keywordid)
        SELECT %s, keywordid
        FROM modulekeywords
        WHERE module_ident = %s""",
                   (new_ident, collection_ident,))
    cursor.execute("""\
        INSERT INTO moduletags (module_ident, tagid)
        SELECT %s, tagid
        FROM moduletags
        WHERE module_ident = %s""",
                   (new_ident, collection_ident,))
    return new_ident

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

    # Is this an insert from legacy? Legacy always supplies the version.
    is_legacy_publication = td['new']['version'] is not None
    if not is_legacy_publication:
        # Bail out, because this trigger only applies to legacy publications.
        return "OK"

    plpy.log('Trigger fired on %s' % (td['new']['moduleid'],))

    with plpydbapi.connect() as db_connection:
        with db_connection.cursor() as cursor:
            modified = republish_module(td, cursor, db_connection)
            plpy.log('modified: {}'.format(modified))
            plpy.log('insert values:\n{}\n'.format('\n'.join([
                '{}: {}'.format(key, value)
                for key, value in td['new'].iteritems()])))
        db_connection.commit()

    return modified


def assign_moduleid_default_trigger(plpy, td):
    """A compatibilty trigger to fill in legacy ``moduleid`` field when
    defined while inserting publications.

    This correctly assigns ``moduleid`` value to
    cnx-publishing publications. This does NOT include
    matching the ``moduleid`` to previous revision by way of ``uuid``.

    This correctly updates the sequence values when a legacy publication
    specifies the ``moduleid`` value. This is because legacy does not know
    about nor use the sequence values when setting legacy ``moduleid``.

    """
    modified_state = "OK"
    portal_type = td['new']['portal_type']
    uuid = td['new']['uuid']
    moduleid = td['new']['moduleid']
    version = td['new']['version']
    major_version = td['new']['major_version']
    minor_version = td['new']['minor_version']

    # Is this an insert from legacy? Legacy always supplies the version.
    is_legacy_publication = version is not None

    if moduleid is None:
        # If the moduleid is not supplied, it is a new publication.
        if portal_type == "Collection":
            prefix, sequence_name = 'col', "collectionid_seq"
        else:
            prefix, sequence_name = 'm', "moduleid_seq"
        plan = plpy.prepare("SELECT $1 || nextval($2)::text AS moduleid",
                            ['text', 'text'])
        row = plpy.execute(plan, (prefix, sequence_name,), 1)
        moduleid = row[0]['moduleid']
        modified_state = "MODIFY"
        td['new']['moduleid'] = moduleid
    elif is_legacy_publication and moduleid is not None:
        # Set the sequence value based on what legacy gave us.
        plan = plpy.prepare("""\
SELECT setval($1, max(substr(moduleid, $2)::int))
FROM (
  SELECT moduleid from modules where portal_type = $3
  UNION ALL
  SELECT $4) AS all_together""", ['text', 'int', 'text', 'text'])
        args = []
        if portal_type == 'Collection':
            args.append('collectionid_seq')
            args.append(4)
        else:
            args.append('moduleid_seq')
            args.append(2)
        args.extend([portal_type, moduleid])
        plpy.execute(plan, args)

    plpy.log("Fixed identifier and version for publication at '{}' " \
             "with the following values: {} and {}" \
             .format(uuid, moduleid, version))

    return modified_state


def assign_version_default_trigger(plpy, td):
    """A compatibilty trigger to fill in legacy data fields that are not
    populated when inserting publications from cnx-publishing.

    If this is not a legacy publication the ``version`` will be set
    based on the ``major_version`` value.
    """
    modified_state = "OK"
    portal_type = td['new']['portal_type']
    version = td['new']['version']
    minor_version = td['new']['minor_version']

    # Set the minor version on collections, because by default it is
    # None/Null, which is the correct default for modules.
    if portal_type == 'Collection' and minor_version is None:
        modified_state = "MODIFY"
        td['new']['minor_version'] = 1

    # Set the legacy version field based on the major version.
    if version is None:
        major_version = td['new']['major_version']
        version = "1.{}".format(major_version)
        modified_state = "MODIFY"
        td['new']['version'] = version

    return modified_state


def assign_document_controls_default_trigger(plpy, td):
    """A compatibilty trigger to fill in ``uuid`` and ``licenseid`` columns
    of the ``document_controls`` table that are not
    populated when inserting publications from legacy.

    This uuid default is not on ``modules.uuid`` column itself,
    because the value needs to be loosely associated
    with the ``document_controls`` entry
    to prevent uuid collisions and bridge the pending publications gap.
    """
    modified_state = "OK"
    uuid = td['new']['uuid']

    # Only do the procedure if this is a legacy publication.
    if uuid is None:
        modified_state = "MODIFY"
        plan = plpy.prepare("""\
INSERT INTO document_controls (uuid, licenseid) VALUES (DEFAULT, $1)
RETURNING uuid""", ('integer',))
        uuid_ = plpy.execute(plan, (td['new']['licenseid'],))[0]['uuid']
        td['new']['uuid'] = uuid_

    return modified_state


def upsert_document_acl_trigger(plpy, td):
    """A compatibility trigger to upsert authorization control entries (ACEs)
    for legacy publications.
    """
    modified_state = "OK"
    uuid_ = td['new']['uuid']
    authors = td['new']['authors'] and td['new']['authors'] or []
    maintainers = td['new']['maintainers'] and td['new']['maintainers'] or []
    is_legacy_publication = td['new']['version'] is not None

    if not is_legacy_publication:
        return modified_state

    # Upsert all authors and maintainers into the ACL
    # to give them publish permission.
    permissibles = []
    permissibles.extend(authors)
    permissibles.extend(maintainers)
    permissibles = set([(uid, 'publish',) for uid in permissibles])

    plan = plpy.prepare("""\
SELECT user_id, permission FROM document_acl WHERE uuid = $1""",
                        ['uuid'])
    existing_permissibles = set([(r['user_id'], r['permission'],)
                                 for r in plpy.execute(plan, (uuid_,))])

    new_permissibles = permissibles.difference(existing_permissibles)

    for uid, permission in new_permissibles:
        plan = plpy.prepare("""\
INSERT INTO document_acl (uuid, user_id, permission)
VALUES ($1, $2, $3)""", ['uuid', 'text', 'permission_type'])
        plpy.execute(plan, (uuid_, uid, permission,))


def upsert_users_from_legacy_publication_trigger(plpy, td):
    """A compatibility trigger to upsert users from the legacy persons table.
    """
    modified_state = "OK"
    uuid_ = td['new']['uuid']
    authors = td['new']['authors'] and td['new']['authors'] or []
    maintainers = td['new']['maintainers'] and td['new']['maintainers'] or []
    licensors = td['new']['licensors'] and td['new']['licensors'] or []
    is_legacy_publication = td['new']['version'] is not None

    if not is_legacy_publication:
        return modified_state

    # Upsert all roles into the users table.
    users = []
    users.extend(authors)
    users.extend(maintainers)
    users.extend(licensors)
    users = list(set(users))

    plan = plpy.prepare("""\
SELECT username FROM users WHERE username = any($1)""",
                        ['text[]'])
    existing_users = set([r['username'] for r in plpy.execute(plan, (users,))])

    new_users = set(users).difference(existing_users)
    for username in new_users:
        plan = plpy.prepare("""\
INSERT INTO users (username, first_name, last_name, full_name, title)
SELECT personid, firstname, surname, fullname, honorific
FROM persons where personid = $1""", ['text'])
        plpy.execute(plan, (username,))

    return modified_state


def insert_users_for_optional_roles_trigger(plpy, td):
    """A compatibility trigger to insert users from moduleoptionalroles
    records. This is primarily for legacy compatibility, but it is not
    possible to tell whether the entry came from legacy or cnx-publishing.
    Therefore, we only insert into users.
    """
    modified_state = "OK"
    users = td['new']['personids'] and td['new']['personids'] or []

    plan = plpy.prepare("""\
SELECT username FROM users WHERE username = any($1)""",
                        ['text[]'])
    existing_users = set([r['username'] for r in plpy.execute(plan, (users,))])

    new_users = set(users).difference(existing_users)
    for username in new_users:
        plan = plpy.prepare("""\
INSERT INTO users (username, first_name, last_name, full_name, title)
SELECT personid, firstname, surname, fullname, honorific
FROM persons where personid = $1""", ['text'])
        plpy.execute(plan, (username,))

    return modified_state


def add_module_file(plpy, td):
    """Postgres database trigger for adding a module file

    When a legacy ``index.cnxml`` is added, this trigger
    transforms it into html and stores it as ``index.cnxml.html``.
    When a cnx-publishing ``index.cnxml.html`` is added, this trigger
    checks if ``index.html.cnxml`` exists before
    transforming it into cnxml and stores it as ``index.html.cnxml``.

    Note, we do not use ``index.html`` over ``index.cnxml.html``, because
    legacy allows users to name files ``index.html``.

    """
    import plpydbapi

    module_ident = td['new']['module_ident']
    fileid = td['new']['fileid']
    filename = td['new']['filename']
    msg = "produce {}->{} for module_ident = {}"

    def check_for(filenames, module_ident):
        """Check for a file at ``filename`` associated with
        module at ``module_ident``.
        """
        stmt = plpy.prepare("""\
SELECT TRUE AS exists FROM module_files
WHERE filename = $1 AND module_ident = $2""", ['text', 'integer'])
        any_exist = False
        for filename in filenames:
            result = plpy.execute(stmt, [filename, module_ident])
            try:
                exists = result[0]['exists']
            except IndexError:
                exists = False
            any_exist = any_exist or exists
        return any_exist

    # Declare the content producer function variable,
    #   because it is possible that it will not be assigned.
    producer_func = None
    if filename == 'index.cnxml':
        new_filenames = ('index.cnxml.html',)
        # Transform content to html.
        other_exists = check_for(new_filenames, module_ident)
        if not other_exists:
            msg = msg.format('cnxml', 'html', module_ident)
            producer_func = produce_html_for_module
    elif filename == 'index.cnxml.html':
        new_filenames = ('index.html.cnxml', 'index.cnxml',)
        # Transform content to cnxml.
        other_exists = check_for(new_filenames, module_ident)
        if not other_exists:
            msg = msg.format('html', 'cnxml', module_ident)
            producer_func = produce_cnxml_for_module
    else:
        # Not one of the special named files.
        return  # skip

    with plpydbapi.connect() as db_connection:
        with db_connection.cursor() as cursor:
            plpy.info(msg)
            if producer_func is not None:
                producer_func(cursor.connection, cursor,
                              module_ident,
                              source_filename=filename,
                              destination_filenames=new_filenames)
            _transform_abstract(cursor, module_ident)
        # For whatever reason, the plpydbapi context manager
        #   does not call commit on close.
        db_connection.commit()
    return


def _transform_abstract(cursor, module_ident):
    """Transforms an abstract using one of content columns
    ('abstract' or 'html') to determine which direction the transform
    will go (cnxml->html or html->cnxml).
    A transform is done on either one of them to make
    the other value. If no value is supplied, the trigger raises an error.
    If both values are supplied, the trigger will skip.
    """
    cursor.execute("""\
SELECT a.abstractid, a.abstract, a.html
FROM modules AS m NATURAL JOIN abstracts AS a
WHERE m.module_ident = %s""", (module_ident,))
    abstractid, cnxml, html = cursor.fetchone()
    if cnxml is not None and html is not None:
        return  # skip
    # TODO Prevent blank abstracts (abstract = null & html = null).

    msg = "produce {}->{} for abstractid={}"
    if cnxml is None:
        # Transform html->cnxml
        msg = msg.format('html', 'cnxml', abstractid)
        content = html
        column = 'abstract'
        transform_func = transform_abstract_to_cnxml
    else:
        # Transform cnxml->html
        msg = msg.format('cnxml', 'html', abstractid)
        content = cnxml
        column = 'html'
        transform_func = transform_abstract_to_html

    content, messages = transform_func(content, module_ident,
                                       cursor.connection)
    cursor.execute(
        "UPDATE abstracts SET {} = %s WHERE abstractid = %s" \
        .format(column),
        (content, abstractid,))
    return msg


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


def get_module_can_publish(cursor, id):
    cursor.execute("""
SELECT DISTINCT user_id
FROM document_acl
WHERE uuid = %s AND permission = 'publish'""", (id,))
    return [i[0] for i in cursor.fetchall()]
