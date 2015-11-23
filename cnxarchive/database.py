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
import json
import psycopg2
import re
import sys

from . import config
from .utils import split_ident_hash


here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
SCHEMA_MANIFEST_FILENAME = 'manifest.json'


def _read_sql_file(name):
    path = os.path.join(SQL_DIRECTORY, '{}.sql'.format(name))
    with open(path, 'r') as fp:
        return fp.read()

SQL = {
    'get-module': _read_sql_file('get-module'),
    'get-content-from-legacy-id': _read_sql_file('get-content-from-legacy-id'),
    'get-content-from-legacy-id-ver': _read_sql_file(
        'get-content-from-legacy-id-ver'),
    'get-module-metadata': _read_sql_file('get-module-metadata'),
    'get-resource': _read_sql_file('get-resource'),
    'get-resource-by-filename': _read_sql_file('get-resource-by-filename'),
    'get-resourceid-by-filename': _read_sql_file('get-resourceid-by-filename'),
    'get-tree-by-uuid-n-version': _read_sql_file('get-tree-by-uuid-n-version'),
    'get-module-versions': _read_sql_file('get-module-versions'),
    'get-module-uuid': _read_sql_file('get-module-uuid'),
    'get-subject-list': _read_sql_file('get-subject-list'),
    'get-featured-links': _read_sql_file('get-featured-links'),
    'get-users-by-ids': _read_sql_file('get-users-by-ids'),
    'get-service-state-messages': _read_sql_file('get-service-state-messages'),
    'get-license-info-as-json': _read_sql_file('get-license-info-as-json'),
    'get-in-book-search': _read_sql_file('get-in-book-search'),
    'get-in-book-search-full-page': _read_sql_file(
        'get-in-book-search-full-page'),
    }


def _read_schema_manifest(manifest_filepath):
    with open(os.path.abspath(manifest_filepath), 'rb') as fp:
        raw_manifest = json.loads(fp.read())
    manifest = []
    relative_dir = os.path.abspath(os.path.dirname(manifest_filepath))
    for item in raw_manifest:
        if isinstance(item, dict):
            file = item['file']
        else:
            file = item
        if os.path.isdir(os.path.join(relative_dir, file)):
            next_manifest = os.path.join(
                relative_dir,
                file,
                SCHEMA_MANIFEST_FILENAME)
            manifest.append(_read_schema_manifest(next_manifest))
        else:
            manifest.append(os.path.join(relative_dir, file))
    return manifest


def _compile_manifest(manifest, content_modifier=None):
    """Compiles a given ``manifest`` into a sequence of schema items.
    Apply the optional ``content_modifier`` to each file's contents.
    """
    items = []
    for item in manifest:
        if isinstance(item, list):
            items.extend(_compile_manifest(item, content_modifier))
        else:
            with open(item, 'rb') as fp:
                content = fp.read()
            if content_modifier:
                content = content_modifier(item, content)
            items.append(content)
    return items


def get_schema():
    manifest_filepath = os.path.join(DB_SCHEMA_DIRECTORY,
                                     SCHEMA_MANIFEST_FILENAME)
    schema_manifest = _read_schema_manifest(manifest_filepath)

    # Modify the file so that it contains comments that say it's origin.
    def file_wrapper(f, c):
        return u"-- FILE: {0}\n{1}\n-- \n".format(f, c)

    return _compile_manifest(schema_manifest, file_wrapper)


def initdb(settings):
    """Initialize the database from the given settings."""
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            for schema_part in get_schema():
                cursor.execute(schema_part)

            # If you are connecting to a database that is not localhost,
            # don't initalize with virtualenv
            db_dict = dict(p.split('=') for p in db_connection.dsn.split())
            if db_dict.get('host', 'localhost') == 'localhost':
                # If virtualenv is active, use that for postgres
                if hasattr(sys, 'real_prefix'):
                    activate_path = os.path.join(
                        os.path.realpath(sys.prefix),
                        'bin/activate_this.py')
                    cursor.execute("SELECT current_database();")
                    db_name = cursor.fetchone()[0]

                    cursor.execute("""SELECT schema_name FROM
                                      information_schema.schemata
                                      WHERE schema_name = 'venv';""")
                    schema_exists = cursor.fetchall()

                    if not schema_exists:
                        cursor.execute("CREATE SCHEMA venv")
                        cursor.execute("ALTER DATABASE \"{}\" SET "
                                       "session_preload_libraries ="
                                       "'session_exec'".format(db_name))
                        cursor.execute("ALTER DATABASE \"{}\" SET "
                                       "session_exec.login_name = "
                                       "'venv.activate_venv'"
                                       .format(db_name))
                        sql = """CREATE FUNCTION venv.activate_venv()
RETURNS void LANGUAGE plpythonu AS $_$
import sys
import os
import site
old_os_path = os.environ['PATH']
os.environ['PATH'] = os.path.dirname(os.path.abspath('{activate_path}')) \
+ os.pathsep + old_os_path
base = os.path.dirname(os.path.dirname(os.path.abspath('{activate_path}')))
site_packages = os.path.join(base, 'lib', 'python%s' % sys.version[:3], \
'site-packages')
prev_sys_path = list(sys.path)
site.addsitedir(site_packages)
sys.real_prefix = sys.prefix
sys.prefix = base
# Move the added items to the front of the path:
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path
$_$""".format(activate_path=activate_path)
                        cursor.execute(sql)


def get_module_ident_from_ident_hash(ident_hash, cursor):
    """Returns the moduleid for a given ``ident_hash``."""
    uuid, (mj_ver, mn_ver) = split_ident_hash(
        ident_hash, split_version=True)
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
    if type(tree) in (type(''), type(u'')):
        import json
        return json.loads(tree)
    else:
        return tree


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
    FROM t JOIN modules m
    ON t.document = m.module_ident''', [collection_ident])
    for i in cursor.fetchall():
        yield i


def get_module_can_publish(cursor, id):
    cursor.execute("""
SELECT DISTINCT user_id
FROM document_acl
WHERE uuid = %s AND permission = 'publish'""", (id,))
    return [i[0] for i in cursor.fetchall()]
