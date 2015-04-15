BEGIN WORK;

DO LANGUAGE plpgsql
$$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_class WHERE relname='modules') THEN
    RAISE EXCEPTION USING MESSAGE = 'Database is already initialized.';
  END IF;
END;
$$;


CREATE EXTENSION IF NOT EXISTS plpythonu;
CREATE FUNCTION uuid_generate_v4 () RETURNS uuid LANGUAGE plpythonu AS $$ import uuid; return uuid.uuid4() $$ ;

CREATE SEQUENCE "moduleid_seq" start 10000 increment 1 maxvalue 2147483647 minvalue 1  cache 1 ;

CREATE SEQUENCE "collectionid_seq" start 10000 increment 1 maxvalue 2147483647 minvalue 1  cache 1 ;


CREATE FUNCTION "comma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '','' || $2 END' LANGUAGE 'sql';

CREATE AGGREGATE list ( BASETYPE = text, SFUNC = comma_cat, STYPE = text, INITCOND = '' );

CREATE FUNCTION "semicomma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '';--;'' || $2 END' LANGUAGE 'sql';

CREATE AGGREGATE semilist ( BASETYPE = text, SFUNC = semicomma_cat, STYPE = text, INITCOND = '' );

CREATE TABLE roles (
    roleid serial PRIMARY KEY,
    roleparam text,
    rolename text,
    roledisplayname text,
    roleattribution text,
    rolecomment text
);

CREATE TABLE moduleoptionalroles (
    module_ident integer,
    roleid integer,
    personids text[]
);

CREATE TABLE "abstracts" (
	"abstractid" serial PRIMARY KEY,
	"abstract" text default NULL,
	"html" text default NULL
);

CREATE TABLE "modulestates" (
        -- Example:  statename = 'current'
	"stateid"    serial PRIMARY KEY,
	"statename"  text
);


CREATE TABLE "licenses" (
       -- Example:  code = 'by'; version = '1.0'; name = 'Attribution';
       --           url = 'http://creativecommons.org/licenses/by/1.0'
       "licenseid"	serial PRIMARY KEY,
       "code"		text,
       "version"	text,
       "name"		text,
       "url"		text,
       "is_valid_for_publication" BOOLEAN DEFAULT FALSE
);


CREATE TABLE "document_controls" (
       -- An association table that is a controlled set of UUID identifiers
       -- for document/module input. This prevents collisions between existing documents,
       -- and publication pending documents, while still providing the publishing system
       -- a means of assigning an identifier where the documents will eventually live.
       -- The 'licenseid' starts as NULL, but if connected to a 'modules' or 'lastest_modules' record MUST be populated, this is enforeced by a trigger.
       "uuid" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       "licenseid" INTEGER DEFAULT NULL
);


CREATE TYPE permission_type AS ENUM (
       'publish'
);

create table "document_acl" (
       "uuid" UUID,
       "user_id" TEXT,
       "permission" permission_type NOT NULL,
       PRIMARY KEY ("uuid", "user_id", "permission"),
       FOREIGN KEY ("uuid") REFERENCES document_controls ("uuid")
);


CREATE TABLE "modules" (
	"module_ident" serial PRIMARY KEY,
	"portal_type" text,
	"moduleid" text,
        -- loosely associated with ``document_controls``.
        "uuid" uuid DEFAULT NULL,
        -- please do not use version in cnx-archive code, it is only used for
        -- storing the legacy version
	"version" text,
	"name" text NOT NULL,
	-- The "created" column contains the date and time for the original publish
	-- for the first version of the document.
	"created" timestamp with time zone NOT NULL default CURRENT_TIMESTAMP,
	"revised" timestamp with time zone NOT NULL default CURRENT_TIMESTAMP,
	"abstractid" integer ,
	"licenseid" integer NOT NULL,
	"doctype" text NOT NULL,
	"submitter" text,
	"submitlog" text,
	"stateid"   integer,
	"parent" integer,
	"language" text,
	"authors" text[],
	"maintainers" text[],
	"licensors" text[],
	"parentauthors" text[],
	"google_analytics" text,
	"buylink" text,
        -- Collections have versions like <major_version>.<minor_version> while
        -- modules have versions like <major_version>
	"major_version" integer default 1,
	"minor_version" integer default NULL,
	"print_style" text,
	FOREIGN KEY (abstractid) REFERENCES "abstracts" DEFERRABLE,
	FOREIGN KEY (stateid) REFERENCES "modulestates" DEFERRABLE,
	FOREIGN KEY (parent) REFERENCES "modules" DEFERRABLE,
	FOREIGN KEY (licenseid) REFERENCES "licenses" DEFERRABLE
);

CREATE INDEX modules_moduleid_idx on modules (moduleid);
CREATE INDEX modules_upmodid_idx ON modules  (upper(moduleid));
CREATE INDEX modules_upname_idx ON modules  (upper(name));
CREATE INDEX modules_portal_type_idx on modules (portal_type);

-- the following needs to be an identical copy of modules as latest_modules
-- except, absence of defaults is intentional

CREATE TABLE "latest_modules" (
	"module_ident" integer,
	"portal_type" text,
	"moduleid" text,
        "uuid" uuid NOT NULL,
        -- please do not use version in cnx-archive code, it is only used for
        -- storing the legacy version
	"version" text,
	"name" text NOT NULL,
	"created" timestamp with time zone NOT NULL,
	"revised" timestamp with time zone NOT NULL,
	"abstractid" integer,
	"licenseid" integer NOT NULL,
	"doctype" text NOT NULL,
	"submitter" text,
	"submitlog" text,
	"stateid"   integer,
	"parent" int,
	"language" text,
	"authors" text[],
	"maintainers" text[],
	"licensors" text[],
	"parentauthors" text[],
	"google_analytics" text,
	"buylink" text,
        -- Collections have versions like <major_version>.<minor_version> while
        -- modules have versions like <major_version>
	"major_version" integer,
	"minor_version" integer,
	"print_style" text
);

CREATE INDEX latest_modules_upmodid_idx ON latest_modules  (upper(moduleid));
CREATE INDEX latest_modules_upname_idx ON latest_modules  (upper(name));
CREATE INDEX latest_modules_moduleid_idx on latest_modules (moduleid);
CREATE INDEX latest_modules_module_ident_idx on latest_modules (module_ident);
CREATE INDEX latest_modules_portal_type_idx on latest_modules (portal_type);

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

CREATE TRIGGER update_latest_version
  BEFORE INSERT OR UPDATE ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_latest();

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
  from cnxarchive.database import assign_version_default_trigger
  return assign_version_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_uuid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_document_controls_default_trigger
  return assign_document_controls_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION upsert_document_acl ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import upsert_document_acl_trigger
  return upsert_document_acl_trigger(plpy, TD)
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

CREATE TRIGGER delete_from_latest_version
  AFTER DELETE ON modules FOR EACH ROW
  EXECUTE PROCEDURE delete_from_latest();

CREATE OR REPLACE FUNCTION optional_roles_user_insert ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import insert_users_for_optional_roles_trigger
  return insert_users_for_optional_roles_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER optional_roles_user_insert
  AFTER INSERT ON moduleoptionalroles FOR EACH ROW
  EXECUTE PROCEDURE optional_roles_user_insert();

CREATE VIEW all_modules as
	SELECT module_ident, uuid, portal_type, moduleid, version, name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM modules
	UNION ALL
	SELECT module_ident, uuid, portal_type, moduleid, 'latest', name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM latest_modules;

CREATE VIEW current_modules AS
       SELECT * FROM modules m
	      WHERE module_ident =
		    (SELECT max(module_ident) FROM modules
			    WHERE m.moduleid = moduleid );

CREATE TABLE "modulefti" (
	"module_ident" integer UNIQUE,
	"module_idx" tsvector,
        "fulltext" text,
	FOREIGN KEY (module_ident) REFERENCES modules ON DELETE CASCADE
);

CREATE INDEX fti_idx ON modulefti USING gist (module_idx);
CREATE TABLE "keywords" (
	"keywordid" serial PRIMARY KEY,
	"word" text NOT NULL
);

CREATE INDEX keywords_upword_idx ON keywords  (upper(word));
CREATE INDEX keywords_word_idx ON keywords  (word);

CREATE TABLE "modulekeywords" (
	"module_ident" integer NOT NULL,
	"keywordid" integer NOT NULL,
	FOREIGN KEY (module_ident) REFERENCES "modules" DEFERRABLE,
	FOREIGN KEY (keywordid) REFERENCES "keywords" DEFERRABLE
);

CREATE INDEX modulekeywords_module_ident_idx ON modulekeywords (module_ident );
CREATE INDEX modulekeywords_keywordid_idx ON modulekeywords (keywordid);
CREATE UNIQUE INDEX modulekeywords_module_ident_keywordid_idx ON
    modulekeywords (module_ident, keywordid );

CREATE TABLE files (
    fileid serial PRIMARY KEY,
    md5 text,
    sha1 text,
    file bytea
);

CREATE INDEX files_md5_idx on files (md5);
CREATE INDEX files_sha1_idx ON files (sha1);

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

CREATE TABLE module_files (
    module_ident integer references modules,
    "uuid" uuid UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    fileid integer references files,
    filename text,
    mimetype text
);

CREATE UNIQUE INDEX module_files_idx ON module_files (module_ident, filename);

CREATE OR REPLACE FUNCTION add_module_file ()
  RETURNS trigger
AS $$
  from cnxarchive.database import add_module_file
  return add_module_file(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER module_file_added
  AFTER INSERT ON module_files FOR EACH ROW
  EXECUTE PROCEDURE add_module_file();

-- Deprecated (3-Feb-2015) Use html_abstract(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_abstract, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_abstract(abstract text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_abstract(<module_ident>')
  import plpydbapi
  from cnxarchive.transforms import transform_abstract_to_html
  db_connection = plpydbapi.connect()
  html_abstract, warning_messages = transform_abstract_to_html(abstract, None, db_connection)
  if warning_messages:
    plpy.warning(warning_messages)
  db_connection.close()
  return html_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_abstract(module_ident int)
  RETURNS text
AS $$
  import plpydbapi
  from cnxarchive.transforms import transform_abstract_to_html
  with plpydbapi.connect() as db_connection:
    with db_connection.cursor() as cursor:
      cursor.execute("SELECT abstract FROM modules NATURAL JOIN abstracts WHERE module_ident = %s", (module_ident,))
      abstract = cursor.fetchone()[0]
    html_abstract, warning_messages = transform_abstract_to_html(abstract, module_ident, db_connection)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_abstract
$$ LANGUAGE plpythonu;

-- Deprecated (3-Feb-2015) Use html_content(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_content, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_content(cnxml text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_content(<module_ident>')
  import plpydbapi
  from cnxarchive.transforms import transform_module_content
  db_connection = plpydbapi.connect()
  html_content, warning_messages = transform_module_content(cnxml, 'cnxml2html', db_connection)
  if warning_messages:
    plpy.warning(warning_messages)
  db_connection.close()
  return html_content
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_content(module_ident int)
  RETURNS text
AS $$
  import plpydbapi
  from cnxarchive.transforms import transform_module_content
  with plpydbapi.connect() as db_connection:
     with db_connection.cursor() as cursor:
          cursor.execute("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = %s AND (filename = 'index.cnxml' OR filename = 'index.html.cnxml')", (module_ident,))
          cnxml = cursor.fetchone()[0]
     content, warning_messages = transform_module_content(cnxml, 'cnxml2html', db_connection, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;


CREATE OR REPLACE FUNCTION cnxml_abstract(module_ident int)
  RETURNS text
AS $$
  import plpydbapi
  from cnxarchive.transforms import transform_abstract_to_cnxml
  with plpydbapi.connect() as db_connection:
     with db_connection.cursor() as cursor:
          cursor.execute("SELECT html FROM modules NATURAL JOIN abstracts WHERE module_ident = %s", (module_ident,))
          abstract = cursor.fetchone()[0]
     cnxml_abstract, warning_messages = transform_abstract_to_cnxml(abstract, module_ident, db_connection)
  if warning_messages:
      plpy.warning(warning_messages)
  return cnxml_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION cnxml_content(module_ident int)
  RETURNS text
AS $$
  import plpydbapi
  from cnxarchive.transforms import transform_module_content
  with plpydbapi.connect() as db_connection:
     with db_connection.cursor() as cursor:
          cursor.execute("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = %s AND filename = 'index.cnxml.html'", (module_ident,))
          html = cursor.fetchone()[0]

     content, warning_messages = transform_module_content(html, 'html2cnxml', db_connection, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;

CREATE TABLE modulecounts (
	countdate date,
	modcount int);

CREATE TABLE similarities (
	objectid text,
	version text,
	sims text[]
);

CREATE UNIQUE INDEX similarities_objectid_version_idx ON similarities (objectid, version);

CREATE OR REPLACE FUNCTION title_order(text) RETURNS text AS $$
begin
if lower(substr($1, 1, 4)) = 'the ' then
 return substr($1, 5);
elsif lower(substr($1,1,3)) = 'an ' then
 return substr($1,4);
elsif lower(substr($1,1,2)) = 'a ' then
 return substr($1,3);
end if;
return $1;
end;
$$ language 'plpgsql' immutable;

create index latest_modules_title_idx on latest_modules (upper(title_order(name)));

CREATE OR REPLACE FUNCTION req(text) RETURNS text AS $$
select regexp_replace($1,E'([.()?[\\]\\{}*+|])',E'\\\\\\1','g')
$$ language sql immutable;

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYELEMENT)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS '
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
';

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYARRAY)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS '
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i:i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
';

CREATE TABLE tags (
    tagid serial PRIMARY KEY,
    tag text,
    scheme text
);

CREATE TABLE moduletags (
    module_ident integer,
    tagid integer,
    FOREIGN KEY (module_ident) REFERENCES modules(module_ident) DEFERRABLE,
    FOREIGN KEY (tagid) REFERENCES tags(tagid) DEFERRABLE
);

CREATE TABLE document_hits (
  documentid INTEGER NOT NULL,
  start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  hits INTEGER DEFAULT 0,
  FOREIGN KEY (documentid) REFERENCES modules (module_ident) ON DELETE CASCADE
);

CREATE TABLE recent_hit_ranks (
  document UUID NOT NULL PRIMARY KEY,
  hits INTEGER DEFAULT 0,
  average FLOAT DEFAULT NULL,
  rank INTEGER DEFAULT NULL
);

CREATE TABLE overall_hit_ranks (
  document UUID NOT NULL PRIMARY KEY,
  hits INTEGER DEFAULT 0,
  average FLOAT DEFAULT NULL,
  rank INTEGER DEFAULT NULL
);

CREATE TABLE users (
  username TEXT NOT NULL PRIMARY KEY,
  created TIMESTAMP WITH TIME ZONE NOT NULL default CURRENT_TIMESTAMP,
  updated TIMESTAMP WITH TIME ZONE NOT NULL default CURRENT_TIMESTAMP,
  first_name TEXT,
  last_name TEXT,
  full_name TEXT,
  suffix TEXT,
  title TEXT,
  -- Used by publishing to moderate the first time publishers.
  is_moderated BOOLEAN
  );

-- =============== --
--   Legacy only   --
-- =============== --

CREATE TABLE "persons" (
  "personid" text PRIMARY KEY,
  "honorific" text,
  "firstname" text,
  "othername" text,
  "surname" text,
  "lineage" text,
  "fullname" text,
  "email" text,
  "homepage" text,
  "comment" text
);

CREATE INDEX person_firstname_upper_idx on persons (upper(firstname));
CREATE INDEX person_surname_upper_idx on persons (upper(surname));
CREATE INDEX person_personid_upper_idx on persons (upper(personid));
CREATE INDEX person_email_upper_idx on persons (upper(email));

COMMIT;
