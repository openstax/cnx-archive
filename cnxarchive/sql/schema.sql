BEGIN WORK;
CREATE SEQUENCE "moduleid_seq" start 10000 increment 1 maxvalue 2147483647 minvalue 1  cache 1 ;


CREATE FUNCTION "comma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '','' || $2 END' LANGUAGE 'sql';

CREATE AGGREGATE list ( BASETYPE = text, SFUNC = comma_cat, STYPE = text, INITCOND = '' );

CREATE FUNCTION "semicomma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '';--;'' || $2 END' LANGUAGE 'sql';

CREATE AGGREGATE semilist ( BASETYPE = text, SFUNC = semicomma_cat, STYPE = text, INITCOND = '' );


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
	"abstract" text NOT NULL
);

CREATE TABLE "modulestates" (
	"stateid"    serial PRIMARY KEY,
	"statename"  text
);


CREATE TABLE "licenses" (
       "licenseid"	serial PRIMARY KEY,
       "code"		text,
       "version"	text,
       "name"		text,
       "url"		text
);


CREATE TABLE "modules" (
	"module_ident" serial PRIMARY KEY,
	"portal_type" text,
	"moduleid" text default 'm' || nextval('"moduleid_seq"'),
	"version" text default '1.1',
	"name" text NOT NULL,
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

CREATE TABLE "latest_modules" (
	"module_ident" integer,
	"portal_type" text,
	"moduleid" text,
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
	"parentauthors" text[]
);

CREATE INDEX latest_modules_upmodid_idx ON latest_modules  (upper(moduleid));
CREATE INDEX latest_modules_upname_idx ON latest_modules  (upper(name));
CREATE INDEX latest_modules_moduleid_idx on latest_modules (moduleid);
CREATE INDEX latest_modules_module_ident_idx on latest_modules (module_ident);
CREATE INDEX latest_modules_portal_type_idx on latest_modules (portal_type);

CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF TG_OP = ''INSERT'' THEN
      DELETE FROM latest_modules WHERE moduleid = NEW.moduleid;
      INSERT into latest_modules ( module_ident,portal_type,moduleid, version, name, 
  		created, revised, abstractid, stateid, doctype, licenseid, 
  		submitter,submitlog, parent, language,
		authors, maintainers, licensors, parentauthors) 
  	VALUES ( NEW.module_ident,NEW.portal_type,NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid, 
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors );
  END IF;

  IF TG_OP = ''UPDATE'' THEN
      UPDATE latest_modules SET
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
	parentauthors=NEW.parentauthors 
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

CREATE TRIGGER delete_from_latest_version 
  AFTER DELETE ON modules FOR EACH ROW 
  EXECUTE PROCEDURE delete_from_latest();

CREATE VIEW all_modules as 
	SELECT module_ident,portal_type,moduleid, version, name, 
			created, revised, abstractid, stateid, doctype, licenseid, 
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors
	FROM modules
	UNION ALL
	SELECT module_ident,portal_type,moduleid, 'latest', name, 
			created, revised, abstractid, stateid, doctype, licenseid, 
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors
	FROM latest_modules;

CREATE VIEW current_modules AS 
       SELECT * FROM modules m 
	      WHERE module_ident = 
		    (SELECT max(module_ident) FROM modules 
			    WHERE m.moduleid = moduleid );

CREATE TABLE "modulefti" (
	"module_ident" integer UNIQUE,
	"module_idx" tsvector,
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
    file bytea
);

CREATE INDEX files_md5_idx on files (md5);

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

CREATE TABLE module_files (
    module_ident integer references modules, 
    fileid integer references files,
    filename text,
    mimetype text
);

CREATE UNIQUE INDEX module_files_idx ON module_files (module_ident, filename);




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

CREATE OR REPLACE FUNCTION fullname (text)
RETURNS TEXT
IMMUTABLE STRICT
LANGUAGE SQL
AS 'SELECT fullname FROM persons WHERE personid = $1;';

CREATE OR REPLACE FUNCTION fullnames (ANYARRAY)
RETURNS TEXT
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS $$ 
DECLARE 
  name text;
  names text;
  id text;
BEGIN
  FOR i IN array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF  i = 1
    THEN
      names = fullname($1[i]);
    ELSE
      names := names ||', ' ||  fullname($1[i]);
    END IF;
  END LOOP;
RETURN names;
END;
$$;


CREATE TABLE tags (
    tagid serial PRIMARY KEY,
    tag text,
    scheme text
);

INSERT INTO tags VALUES (0, 'Test/Draft', 'internal');
INSERT INTO tags VALUES (1, 'Arts', 'ISKME subject');
INSERT INTO tags VALUES (2, 'Business', 'ISKME subject');
INSERT INTO tags VALUES (3, 'Humanities', 'ISKME subject');
INSERT INTO tags VALUES (4, 'Mathematics and Statistics', 'ISKME subject');
INSERT INTO tags VALUES (5, 'Science and Technology', 'ISKME subject');
INSERT INTO tags VALUES (6, 'Social Sciences', 'ISKME subject');



CREATE TABLE moduletags (
    module_ident integer,
    tagid integer,
    FOREIGN KEY (module_ident) REFERENCES modules(module_ident) DEFERRABLE,
    FOREIGN KEY (tagid) REFERENCES tags(tagid) DEFERRABLE
);

CREATE TABLE moduleratings(
    module_ident integer,
    totalrating integer,
    votes integer,
    FOREIGN KEY (module_ident) REFERENCES modules(module_ident) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION register_rating(integer, integer) RETURNS boolean AS '
DECLARE
    id ALIAS FOR $1;
    rating ALIAS FOR $2;
BEGIN
    UPDATE moduleratings SET totalrating=totalrating+rating,votes=votes+1 WHERE module_ident=id;
    IF NOT FOUND THEN
        INSERT INTO moduleratings (module_ident,totalrating,votes) VALUES (id, rating, 1);
    END IF;
    RETURN FOUND;
END
' LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deregister_rating(integer, integer) RETURNS boolean AS '
DECLARE
    id ALIAS FOR $1;
    rating ALIAS FOR $2;
BEGIN
    UPDATE moduleratings SET totalrating=totalrating-rating,votes=votes-1 WHERE module_ident=id;
    RETURN FOUND;
END
' LANGUAGE plpgsql;

COMMIT;
