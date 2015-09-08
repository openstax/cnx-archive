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
  from cnxarchive.database import republish_module_trigger
  return republish_module_trigger(plpy, TD)
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
  from cnxarchive.database import upsert_users_from_legacy_publication_trigger
  return upsert_users_from_legacy_publication_trigger(plpy, TD)
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
  from cnxarchive.database import insert_users_for_optional_roles_trigger
  return insert_users_for_optional_roles_trigger(plpy, TD)
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
