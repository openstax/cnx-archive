# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database models and utilities."""
import os
import json
import psycopg2
import logging

import cnxdb
from pyramid.threadlocal import get_current_registry

from . import config
from cnxmltransforms import (
    produce_cnxml_for_module, produce_html_for_module,
    transform_abstract_to_cnxml, transform_abstract_to_html,
    )
from .utils import split_ident_hash, IdentHashMissingVersion

here = os.path.abspath(os.path.dirname(__file__))
CNXDB_DIRECTORY = os.path.abspath(os.path.dirname(cnxdb.__file__))
SQL_DIRECTORY = os.path.join(CNXDB_DIRECTORY, 'archive-sql')

logger = logging.getLogger('cnxarchive')


class ContentNotFound(Exception):
    """Used when database retrival fails."""

    pass


def _read_sql_file(name):
    path = os.path.join(SQL_DIRECTORY, '{}.sql'.format(name))
    with open(path, 'r') as fp:
        return fp.read()

SQL = {
    'get-available-languages-and-count': _read_sql_file(
        'get-available-languages-and-count'),
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
    'get-in-collated-book-search': _read_sql_file(
        'get-in-collated-book-search'),
    'get-in-collated-book-search-full-page': _read_sql_file(
        'get-in-collated-book-search-full-page'),
    'get-collated-content': _read_sql_file('get-collated-content'),
    'get-collated-state': _read_sql_file('get-collated-state'),
    }


def db_connect(connection_string=None):
    """Function to supply a database connection object."""
    if connection_string is None:
        settings = get_current_registry().settings
        connection_string = settings[config.CONNECTION_STRING]
    return psycopg2.connect(connection_string)


def get_module_ident_from_ident_hash(ident_hash, cursor):
    """Return the moduleid for a given ``ident_hash``."""
    try:
        uuid, (mj_ver, mn_ver) = split_ident_hash(
            ident_hash, split_version=True)
    except IdentHashMissingVersion as e:
        uuid, mj_ver, mn_ver = e.id, None, None
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


def get_tree(ident_hash, cursor, as_collated=False):
    """Return a JSON representation of the binder tree for ``ident_hash``."""
    uuid, version = split_ident_hash(ident_hash)
    cursor.execute(SQL['get-tree-by-uuid-n-version'],
                   (uuid, version, as_collated,))
    try:
        tree = cursor.fetchone()[0]
    except TypeError:  # NoneType
        raise ContentNotFound()
    if type(tree) in (type(''), type(u'')):
        return json.loads(tree)
    else:
        return tree


def get_collated_content(ident_hash, context_ident_hash, cursor):
    """Return collated content for ``ident_hash``."""
    cursor.execute(SQL['get-collated-content'],
                   (ident_hash, context_ident_hash,))
    try:
        return cursor.fetchone()[0]
    except TypeError:  # NoneType
        return


def get_module_uuid(plpy, moduleid):
    """Retrieve page uuid from legacy moduleid."""
    plan = plpy.prepare("SELECT uuid FROM modules WHERE moduleid = $1;",
                        ('text',))
    result = plpy.execute(plan, (moduleid,), 1)
    if result:
        return result[0]['uuid']


def get_current_module_ident(moduleid, plpy):
    """Retrieve module_ident for a given moduleid.

    Note that module_ident is used only for internal database relational
    associations, and is equivalent to a uuid@version for a given document.
    """
    plan = plpy.prepare('''\
        SELECT m.module_ident FROM modules m
        WHERE m.moduleid = $1 ORDER BY revised DESC''', ('text',))
    results = plpy.execute(plan, (moduleid,), 1)
    if results:
        return results[0]['module_ident']


def set_version(portal_type, legacy_version, td):
    """Set the major_version and minor_version if they are not set."""
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
        # N.B. a very few older modules had major=2 and minor zero-based.
        # The odd math below adds one to the minor for those
        modified = 'MODIFY'
        td['new']['major_version'] = int(legacy_minor)+(int(legacy_major)-1)
        td['new']['minor_version'] = None

    return modified


def get_collection_tree(collection_ident, cursor):
    """Build and retrieve json tree representation of a book."""
    cursor.execute('''
    WITH RECURSIVE t(node, parent, document, path) AS (
        SELECT tr.nodeid, tr.parent_id, tr.documentid, ARRAY[tr.nodeid]
        FROM trees tr
        WHERE tr.documentid = %s and tr.is_collated = 'False'
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
    """Return userids allowed to publish this book."""
    cursor.execute("""
SELECT DISTINCT user_id
FROM document_acl
WHERE uuid = %s AND permission = 'publish'""", (id,))
    return [i[0] for i in cursor.fetchall()]
