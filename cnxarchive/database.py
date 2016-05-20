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
import sys
import logging

from pyramid.threadlocal import get_current_registry

from . import config
from .transforms import (
    produce_cnxml_for_module, produce_html_for_module,
    transform_abstract_to_cnxml, transform_abstract_to_html,
    )
from .utils import split_ident_hash, IdentHashMissingVersion

here = os.path.abspath(os.path.dirname(__file__))
SQL_DIRECTORY = os.path.join(here, 'sql')
DB_SCHEMA_DIRECTORY = os.path.join(SQL_DIRECTORY, 'schema')
SCHEMA_MANIFEST_FILENAME = 'manifest.json'

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
    'get-collated-content': _read_sql_file('get-collated-content'),
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
    """Compile a given ``manifest`` into a sequence of schema items.

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


def db_connect(connection_string=None):
    """Function to supply a database connection object."""
    if connection_string is None:
        settings = get_current_registry().settings
        connection_string = settings[config.CONNECTION_STRING]
    return psycopg2.connect(connection_string)


def get_schema():
    """Return the current schema."""
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
                        try:
                            cursor.execute("SAVEPOINT session_preload")
                            cursor.execute("ALTER DATABASE \"{}\" SET "
                                           "session_preload_libraries ="
                                           "'session_exec'".format(db_name))
                        except psycopg2.ProgrammingError, e:
                            if e.message.startswith(
                                    'unrecognized configuration parameter'):

                                cursor.execute("ROLLBACK TO SAVEPOINT "
                                               "session_preload")
                                logger.warning("Postgresql < 9.4: make sure "
                                               "to set "
                                               "'local_preload_libraries "
                                               "= session_exec' in "
                                               "postgresql.conf and restart")
                            else:
                                raise

                        cursor.execute("ALTER DATABASE \"{}\" SET "
                                       "session_exec.login_name = "
                                       "'venv.activate_venv'"
                                       .format(db_name))
                        sql = """CREATE FUNCTION venv.activate_venv()
RETURNS void LANGUAGE plpythonu AS $_$
import sys
import os
import site
old_os_path = os.environ.get('PATH','')
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
        import json
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


def get_minor_version(module_ident, plpy):
    """Retrieve minor version only given module_ident."""
    plan = plpy.prepare('''\
        SELECT m.minor_version
            FROM modules m
            WHERE m.module_ident = $1
            ORDER BY m.revised DESC''', ('integer',))
    results = plpy.execute(plan, (module_ident,), 1)
    return results[0]['minor_version']


def next_version(module_ident, plpy):
    """Determine next minor version for a given module_ident.

    Note potential race condition!
    """
    minor = get_minor_version(module_ident, plpy)
    return minor + 1


def get_collections(module_ident, plpy):
    """Get all the collections that the module is part of."""
    plan = plpy.prepare('''
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
    FROM t JOIN latest_modules m ON (t.document = m.module_ident)
    WHERE t.parent IS NULL
    ''', ('integer',))
    for i in plpy.execute(plan, (module_ident,)):
        yield i['module_ident']


def rebuild_collection_tree(old_collection_ident, new_document_id_map, plpy):
    """Create a new tree for the collection based on the old tree.

    This usesnew document ids, replacing old ones.
    """
    get_tree = plpy.prepare('''
    WITH RECURSIVE t(node, parent, document, title, childorder, latest, path)
        AS (SELECT tr.nodeid, tr.parent_id, tr.documentid, tr.title,
                   tr.childorder, tr.latest, ARRAY[tr.nodeid]
            FROM trees tr
            WHERE tr.documentid = $1
    UNION ALL
        SELECT c.nodeid, c.parent_id, c.documentid, c.title,
               c.childorder, c.latest, path || ARRAY[c.nodeid]
        FROM trees c JOIN t ON (c.parent_id = t.node)
        WHERE not c.nodeid = ANY(t.path)
    )
    SELECT * FROM t
    ''', ('integer',))

    def get_old_tree():
        return plpy.execute(get_tree, (old_collection_ident,))

    tree = {}  # { old_nodeid: {'data': ...}, ...}
    children = {}  # { nodeid: [child_nodeid, ...], child_nodeid: [...]}
    for i in get_old_tree():
        tree[i['node']] = {'data': i, 'new_nodeid': None}
        children.setdefault(i['parent'], [])
        children[i['parent']].append(i['node'])

    insert_tree = plpy.prepare('''
    INSERT INTO trees (nodeid, parent_id, documentid,
        title, childorder, latest)
    VALUES (DEFAULT, $1, $2, $3, $4, $5)
    RETURNING nodeid
    ''', ('integer', 'integer', 'text', 'integer', 'boolean'))

    def execute(fields):
        results = plpy.execute(insert_tree, fields, 1)
        return results[0]['nodeid']

    root_node = children[None][0]

    def build_tree(node, parent):
        data = tree[node]['data']
        new_node = execute([parent, new_document_id_map.get(data['document'],
                            data['document']), data['title'],
                            data['childorder'], data['latest']])
        for i in children.get(node, []):
            build_tree(i, new_node)
    build_tree(root_node, None)


def republish_collection(next_minor_version, collection_ident, plpy,
                         revised=None):
    """Insert a new row for collection_ident with a new version.

    Returns the module_ident of the row inserted.
    """
    sql = '''
    INSERT INTO modules (portal_type, moduleid, uuid, version, name, created,
        revised, abstractid, licenseid, doctype, submitter, submitlog,
        stateid, parent, language, authors, maintainers, licensors,
        parentauthors, google_analytics, buylink, print_style,
        major_version, minor_version)
      SELECT m.portal_type, m.moduleid, m.uuid, m.version, m.name, m.created,
        {}, m.abstractid, m.licenseid, m.doctype, m.submitter, m.submitlog,
        m.stateid, m.parent, m.language, m.authors, m.maintainers, m.licensors,
        m.parentauthors, m.google_analytics, m.buylink, m.print_style,
        m.major_version, $1
      FROM modules m
      WHERE m.module_ident = $2
    RETURNING module_ident
    '''
    if revised is None:
        sql = sql.format('CURRENT_TIMESTAMP')
        types = ('integer', 'integer')
        params = (next_minor_version, collection_ident)
    else:
        sql = sql.format('$3')
        types = ('integer', 'integer', 'timestamp')
        params = (next_minor_version, collection_ident, revised)
    plan = plpy.prepare(sql, types)
    new_ident = plpy.execute(plan, params, 1)[0]['module_ident']

    plan = plpy.prepare("""\
        INSERT INTO modulekeywords (module_ident, keywordid)
        SELECT $1, keywordid
        FROM modulekeywords
        WHERE module_ident = $2""", ('integer', 'integer'))
    plpy.execute(plan, (new_ident, collection_ident,))

    plan = plpy.prepare("""\
        INSERT INTO moduletags (module_ident, tagid)
        SELECT $1, tagid
        FROM moduletags
        WHERE module_ident = $2""", ('integer', 'integer'))
    plpy.execute(plan, (new_ident, collection_ident,))
    return new_ident


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


def republish_module(td, plpy):
    """When a module is republished, create new minor versions of collections.

    All collections that this module is contained in part of will need to be
    updated (a minor update).


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

    current_module_ident = get_current_module_ident(moduleid, plpy)
    if current_module_ident:
        # need to overide autogen uuid to keep it constant per moduleid
        uuid = get_module_uuid(plpy, moduleid)
        td['new']['uuid'] = uuid
        modified = 'MODIFY'
    else:
        # nothing to do if the module/collection is new
        return modified

    if portal_type != 'Module':
        # nothing else to do if something else is being published
        return modified

    # Module is republished
    for collection_id in get_collections(current_module_ident, plpy):
        minor = next_version(collection_id, plpy)
        new_ident = republish_collection(minor, collection_id, plpy)
        rebuild_collection_tree(collection_id, {
            collection_id: new_ident,
            current_module_ident: td['new']['module_ident'],
            }, plpy)

    return modified


def republish_module_trigger(plpy, td):
    """Trigger called from postgres database when republishing a module.

    When a module is republished, the versions of the collections that it is
    part of will need to be updated (a minor update).


    e.g. there is a collection c1 v2.1, which contains module m1 v3

    m1 is updated, we have a new row in the modules table with m1 v4

    this trigger will create increment the minor version of c1, so we'll have
    c1 v2.2

    we need to create a collection tree for c1 v2.2 which is exactly the same
    as c1 v2.1, but with m1 v4 instead of m1 v3, and c1 v2.2 instead of c1 v2.2
    """
    # Is this an insert from legacy? Legacy always supplies the version.
    is_legacy_publication = td['new']['version'] is not None
    if not is_legacy_publication:
        # Bail out, because this trigger only applies to legacy publications.
        return "OK"

    plpy.log('Trigger fired on %s' % (td['new']['moduleid'],))

    modified = republish_module(td, plpy)
    plpy.log('modified: {}'.format(modified))
    plpy.log('insert values:\n{}\n'.format('\n'.join([
        '{}: {}'.format(key, value)
        for key, value in td['new'].iteritems()])))

    return modified


def assign_moduleid_default_trigger(plpy, td):
    """Trigger to fill in legacy ``moduleid`` when publishing.

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

    plpy.log("Fixed identifier and version for publication at '{}' "
             "with the following values: {} and {}"
             .format(uuid, moduleid, version))

    return modified_state


def assign_version_default_trigger(plpy, td):
    """Trigger to fill in legacy data fields.

    A compatibilty trigger to fill in legacy data fields that are not
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
    """Trigger to fill in document_controls when legacy publishes.

    A compatibilty trigger to fill in ``uuid`` and ``licenseid`` columns
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
    """Trigger for filling in acls when legacy publishes.

    A compatibility trigger to upsert authorization control entries (ACEs)
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
    """A compatibility trigger to upsert users from legacy persons table."""
    modified_state = "OK"
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
    """Trigger to update users from optional roles entries.

    A compatibility trigger to insert users from moduleoptionalroles
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
    """Database trigger for adding a module file.

    When a legacy ``index.cnxml`` is added, this trigger
    transforms it into html and stores it as ``index.cnxml.html``.
    When a cnx-publishing ``index.cnxml.html`` is added, this trigger
    checks if ``index.html.cnxml`` exists before
    transforming it into cnxml and stores it as ``index.html.cnxml``.

    Note, we do not use ``index.html`` over ``index.cnxml.html``, because
    legacy allows users to name files ``index.html``.

    """
    module_ident = td['new']['module_ident']
    filename = td['new']['filename']
    msg = "produce {}->{} for module_ident = {}"

    def check_for(filenames, module_ident):
        """Find filenames associated with module_ident.

        Check for a file at ``filename`` associated with
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

    plpy.info(msg)
    if producer_func is not None:
        producer_func(plpy,
                      module_ident,
                      source_filename=filename,
                      destination_filenames=new_filenames)
    _transform_abstract(plpy, module_ident)
    return


def _transform_abstract(plpy, module_ident):
    """Transform abstract, bi-directionally.

    Transforms an abstract using one of content columns
    ('abstract' or 'html') to determine which direction the transform
    will go (cnxml->html or html->cnxml).
    A transform is done on either one of them to make
    the other value. If no value is supplied, the trigger raises an error.
    If both values are supplied, the trigger will skip.
    """
    plan = plpy.prepare("""\
SELECT a.abstractid, a.abstract, a.html
FROM modules AS m NATURAL JOIN abstracts AS a
WHERE m.module_ident = $1""", ('integer',))
    result = plpy.execute(plan, (module_ident,), 1)[0]
    abstractid, cnxml, html = (
        result['abstractid'], result['abstract'], result['html'])
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

    content, messages = transform_func(content, module_ident, plpy)
    plan = plpy.prepare(
        "UPDATE abstracts SET {} = $1 WHERE abstractid = $2".format(column),
        ('text', 'integer'))
    plpy.execute(plan, (content, abstractid,))
    return msg


def get_collection_tree(collection_ident, cursor):
    """Build and retrieve json tree representation of a book."""
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
    """Return userids allowed to publish this book."""
    cursor.execute("""
SELECT DISTINCT user_id
FROM document_acl
WHERE uuid = %s AND permission = 'publish'""", (id,))
    return [i[0] for i in cursor.fetchall()]
