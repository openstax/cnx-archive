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

from cnxmltransforms import (
    produce_cnxml_for_module, produce_html_for_module,
    transform_abstract_to_cnxml, transform_abstract_to_html,
    )

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
    if type(tree) in (type(''), type(u'')):
        import json
        return json.loads(tree)
    else:
        return tree


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
        "UPDATE abstracts SET {} = %s WHERE abstractid = %s"
        .format(column), (content, abstractid,))
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
