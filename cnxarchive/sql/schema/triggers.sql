CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF TG_OP = ''INSERT'' AND
          NEW.revised >= ((SELECT revised FROM modules
              WHERE uuid = NEW.uuid ORDER BY revised DESC LIMIT 1)
              UNION ALL VALUES (NEW.revised) LIMIT 1) THEN
      DELETE FROM latest_modules WHERE moduleid = NEW.moduleid;
      INSERT into latest_modules (
                uuid, module_ident, portal_type, moduleid, version, name,
  		created, revised, abstractid, stateid, doctype, licenseid,
  		submitter,submitlog, parent, language,
		authors, maintainers, licensors, parentauthors, google_analytics,
                major_version, minor_version, print_style)
  	VALUES (
         NEW.uuid, NEW.module_ident, NEW.portal_type, NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid,
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors, NEW.google_analytics,
         NEW.major_version, NEW.minor_version, NEW.print_style);
  END IF;

  IF TG_OP = ''UPDATE'' THEN
      UPDATE latest_modules SET
        uuid=NEW.uuid,
        moduleid=NEW.moduleid,
        portal_type=NEW.portal_type,
        version=NEW.version,
        name=NEW.name,
        created=NEW.created,
        revised=NEW.revised,
        abstractid=NEW.abstractid,
        stateid=NEW.stateid,
        doctype=NEW.doctype,
        licenseid=NEW.licenseid,
	submitter=NEW.submitter,
	submitlog=NEW.submitlog,
        parent=NEW.parent,
	language=NEW.language,
	authors=NEW.authors,
	maintainers=NEW.maintainers,
	licensors=NEW.licensors,
	parentauthors=NEW.parentauthors,
	google_analytics=NEW.google_analytics,
        major_version=NEW.major_version,
        minor_version=NEW.minor_version,
        print_style=NEW.print_style
        WHERE module_ident=NEW.module_ident;
  END IF;

RETURN NEW;
END;

' LANGUAGE 'plpgsql';

CREATE TRIGGER update_latest_version
  BEFORE INSERT OR UPDATE ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_latest();




CREATE OR REPLACE FUNCTION delete_from_latest() RETURNS trigger AS '
BEGIN
  DELETE FROM  latest_modules
    WHERE module_ident=OLD.module_ident;
  IF FOUND THEN
    INSERT into latest_modules select * from current_modules where moduleid=OLD.moduleid;
  END IF;
  RETURN OLD;
END;
' LANGUAGE 'plpgsql';

CREATE TRIGGER delete_from_latest_version
  AFTER DELETE ON modules FOR EACH ROW
  EXECUTE PROCEDURE delete_from_latest();




CREATE OR REPLACE FUNCTION republish_module ()
  RETURNS trigger
AS $$
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

    def set_version(portal_type, legacy_version):
        """Sets the major_version and minor_version if they are not set
        """
        major = TD['new']['major_version']
        minor = TD['new']['minor_version']
        modified = 'OK'
        legacy_major, legacy_minor = legacy_version.split('.')

        if portal_type == 'Collection':
            # For collections, both major and minor needs to be set
            modified = 'MODIFY'
            TD['new']['major_version'] = int(legacy_minor)
            if TD['new']['minor_version'] is None:
                TD['new']['minor_version'] = 1

        elif portal_type == 'Module':
            # For modules, major should be set and minor should be None
            # N.B. a very few older modules had major=2 and minor zero-based. Add one for those
            modified = 'MODIFY'
            TD['new']['major_version'] = int(legacy_minor) + (int(legacy_major) - 1)
            TD['new']['minor_version'] = None

        return modified

    def get_current_module_ident(moduleid):
        sql = '''SELECT module_ident FROM modules
                 WHERE moduleid = $1 ORDER BY revised DESC'''
        plan = plpy.prepare(sql, ('text',))
        results = plpy.execute(plan, (moduleid,), 1)
        if results:
            return results[0]['module_ident']

    def get_module_uuid(moduleid):
        plan = plpy.prepare('SELECT uuid FROM modules WHERE moduleid = $1',
                            ('text',))
        result = plpy.execute(plan, (moduleid,), 1)
        if result:
            return result[0]['uuid']

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
        FROM t JOIN latest_modules m ON (t.document = m.module_ident)
        WHERE t.parent IS NULL
        '''
        plan = plpy.prepare(sql, ('integer',))
        for i in plpy.execute(plan, (module_ident,)):
            yield i['module_ident']

    def next_version(module_ident):
        minor = get_minor_version(module_ident)
        return minor + 1

    def get_minor_version(module_ident):
        sql = '''SELECT minor_version
                FROM modules
                WHERE module_ident = $1
                ORDER BY revised DESC'''
        plan = plpy.prepare(sql, ('integer',))
        results = plpy.execute(plan, (module_ident,), 1)
        if results:
            return results[0]['minor_version']

    def republish_collection(next_minor_version, collection_ident,
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
            m.google_analytics, m.buylink, m.major_version, $1
          FROM modules m
          WHERE m.module_ident = $2
        RETURNING module_ident
        '''
        if revised is None:
            sql = sql.format('CURRENT_TIMESTAMP')
            plan = plpy.prepare(sql, ('integer', 'integer'))
            params = (next_minor_version, collection_ident)
        else:
            sql = sql.format('$3')
            plan = plpy.prepare(sql, ('integer', 'integer', 'timestamp'))
            params = (next_minor_version, collection_ident, revised)

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

    def rebuild_collection_tree(old_collection_ident, new_document_id_map):
        """Create a new tree for the collection based on the old tree but with
        new document ids
        """
        sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr WHERE tr.documentid = $1
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON (c.parent_id = t.node)
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t
        '''

        def get_tree():
            plan = plpy.prepare(sql, ('integer',))
            for i in plpy.execute(plan, (old_collection_ident,)):
                yield i

        tree = {} # { old_nodeid: {'data': ...}, ...}
        children = {} # { nodeid: [child_nodeid, ...], child_nodeid: [...]}
        for i in get_tree():
            tree[i['node']] = {'data': i, 'new_nodeid': None}
            children.setdefault(i['parent'], [])
            children[i['parent']].append(i['node'])

        sql = '''
        INSERT INTO trees (nodeid, parent_id, documentid, title, childorder, latest)
        VALUES (DEFAULT, $1, $2, $3, $4, $5)
        RETURNING nodeid
        '''
        plan = plpy.prepare(sql, ('integer', 'integer', 'text', 'integer', 'boolean',))

        def execute(fields):
            return plpy.execute(plan, fields, 1)[0]['nodeid']

        root_node = children[None][0]
        def build_tree(node, parent):
            data = tree[node]['data']
            new_node = execute([parent, new_document_id_map.get(data['document'],
                data['document']), data['title'], data['childorder'],
                data['latest']])
            for i in children.get(node, []):
                build_tree(i, new_node)
        build_tree(root_node, None)

    def republish_module():
        """When a module is republished, the versions of the collections that it is
        part of will need to be updated (a minor update).


        e.g. there is a collection c1 v2.1, which contains module m1 v3

        m1 is updated, we have a new row in the modules table with m1 v4

        this trigger will create increment the minor version of c1, so we'll have
        c1 v2.2

        we need to create a collection tree for c1 v2.2 which is exactly the same
        as c1 v2.1, but with m1 v4 instead of m1 v3, and c1 v2.2 instead of c1 v2.2
        """
        portal_type = TD['new']['portal_type']
        modified = 'OK'
        moduleid = TD['new']['moduleid']
        legacy_version = TD['new']['version']

        modified = set_version(portal_type, legacy_version)

        current_module_ident = get_current_module_ident(moduleid)
        if current_module_ident:
            # need to overide autogen uuid to keep it constant per moduleid
            uuid = get_module_uuid(moduleid)
            TD['new']['uuid'] = uuid
            modified = 'MODIFY'
        else:
            # nothing to do if the module/collection is new
            return modified

        if portal_type != 'Module':
            # nothing else to do if something else is being published
            return modified

        new_module_ident = TD['new']['module_ident']
        # Module is republished
        for collection_id in get_collections(current_module_ident):
            minor = next_version(collection_id)
            new_ident = republish_collection(minor, collection_id)
            rebuild_collection_tree(collection_id, {
                collection_id: new_ident,
                current_module_ident: new_module_ident,
                })

        return modified

    # Is this an insert from legacy? Legacy always supplies the version.
    is_legacy_publication = TD['new']['version'] is not None
    if not is_legacy_publication:
        # Bail out, because this trigger only applies to legacy publications.
        return "OK"

    plpy.log('Trigger fired on %s' % (TD['new']['moduleid'],))

    modified = republish_module()
    plpy.log('modified: {}'.format(modified))
    plpy.log('insert values:\n{}\n'.format('\n'.join([
        '{}: {}'.format(key, value)
        for key, value in TD['new'].iteritems()])))

    return modified
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_moduleid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_moduleid_default_trigger
  return assign_moduleid_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_version_default ()
  RETURNS TRIGGER
AS $$
    """A compatibilty trigger to fill in legacy data fields that are not
    populated when inserting publications from cnx-publishing.

    If this is not a legacy publication the ``version`` will be set
    based on the ``major_version`` value.
    """
    modified_state = "OK"
    portal_type = TD['new']['portal_type']
    version = TD['new']['version']
    minor_version = TD['new']['minor_version']

    # Set the minor version on collections, because by default it is
    # None/Null, which is the correct default for modules.
    if portal_type == 'Collection' and minor_version is None:
        modified_state = "MODIFY"
        TD['new']['minor_version'] = 1

    # Set the legacy version field based on the major version.
    if version is None:
        major_version = TD['new']['major_version']
        version = "1.{}".format(major_version)
        modified_state = "MODIFY"
        TD['new']['version'] = version

    return modified_state
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_uuid_default ()
  RETURNS TRIGGER
AS $$
    """A compatibilty trigger to fill in ``uuid`` and ``licenseid`` columns
    of the ``document_controls`` table that are not
    populated when inserting publications from legacy.

    This uuid default is not on ``modules.uuid`` column itself,
    because the value needs to be loosely associated
    with the ``document_controls`` entry
    to prevent uuid collisions and bridge the pending publications gap.
    """
    modified_state = "OK"
    uuid = TD['new']['uuid']

    # Only do the procedure if this is a legacy publication.
    if uuid is None:
        modified_state = "MODIFY"
        plan = plpy.prepare("""\
INSERT INTO document_controls (uuid, licenseid) VALUES (DEFAULT, $1)
RETURNING uuid""", ('integer',))
        uuid_ = plpy.execute(plan, (TD['new']['licenseid'],))[0]['uuid']
        TD['new']['uuid'] = uuid_

    return modified_state
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION upsert_document_acl ()
  RETURNS TRIGGER
AS $$
    """A compatibility trigger to upsert authorization control entries (ACEs)
    for legacy publications.
    """
    modified_state = "OK"
    uuid_ = TD['new']['uuid']
    authors = TD['new']['authors'] and TD['new']['authors'] or []
    maintainers = TD['new']['maintainers'] and TD['new']['maintainers'] or []
    is_legacy_publication = TD['new']['version'] is not None

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
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION upsert_user_shadow ()
  RETURNS TRIGGER
AS $$
    """A compatibility trigger to upsert users from the legacy persons table.
    """
    modified_state = "OK"
    uuid_ = TD['new']['uuid']
    authors = TD['new']['authors'] and TD['new']['authors'] or []
    maintainers = TD['new']['maintainers'] and TD['new']['maintainers'] or []
    licensors = TD['new']['licensors'] and TD['new']['licensors'] or []
    is_legacy_publication = TD['new']['version'] is not None

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
$$ LANGUAGE plpythonu;

CREATE TRIGGER act_10_module_uuid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_uuid_default();

CREATE TRIGGER act_20_module_acl_upsert
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE upsert_document_acl();

CREATE TRIGGER act_80_legacy_module_user_upsert
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE upsert_user_shadow();

CREATE TRIGGER module_moduleid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_moduleid_default();

CREATE TRIGGER module_published
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE republish_module();

CREATE TRIGGER module_version_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_version_default();




CREATE OR REPLACE FUNCTION optional_roles_user_insert ()
  RETURNS TRIGGER
AS $$
    """A compatibility trigger to insert users from moduleoptionalroles
    records. This is primarily for legacy compatibility, but it is not
    possible to tell whether the entry came from legacy or cnx-publishing.
    Therefore, we only insert into users.
    """
    modified_state = "OK"
    users = TD['new']['personids'] and TD['new']['personids'] or []

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
$$ LANGUAGE plpythonu;

CREATE TRIGGER optional_roles_user_insert
  AFTER INSERT ON moduleoptionalroles FOR EACH ROW
  EXECUTE PROCEDURE optional_roles_user_insert();




CREATE FUNCTION update_md5() RETURNS "trigger"
    AS $$
BEGIN
  NEW.md5 = md5(NEW.file);
  RETURN NEW;
END;
$$
    LANGUAGE plpgsql;

CREATE TRIGGER update_file_md5
    BEFORE INSERT OR UPDATE ON files
    FOR EACH ROW
    EXECUTE PROCEDURE update_md5();

CREATE OR REPLACE FUNCTION update_sha1()
    RETURNS TRIGGER
AS $$
    import hashlib

    TD['new']['sha1'] = hashlib.new('sha1', TD['new']['file']).hexdigest()
    return 'MODIFY'
$$ LANGUAGE plpythonu;

CREATE TRIGGER update_files_sha1
    BEFORE INSERT OR UPDATE ON files
    FOR EACH ROW
    EXECUTE PROCEDURE update_sha1();




CREATE OR REPLACE FUNCTION add_module_file ()
  RETURNS trigger
AS $$
  from cnxarchive.database import add_module_file
  return add_module_file(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER module_file_added
  AFTER INSERT ON module_files FOR EACH ROW
  EXECUTE PROCEDURE add_module_file();
