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
	"stateid"   integer DEFAULT 1,
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
	"stateid"   integer DEFAULT 1,
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

CREATE TABLE "modulefti" (
	"module_ident" integer UNIQUE,
	"module_idx" tsvector,
        "fulltext" text,
	FOREIGN KEY (module_ident) REFERENCES modules ON DELETE CASCADE
);

CREATE TABLE "modulefti_lexemes" (
	"module_ident" integer,
	"lexeme" text,
    "positions" int[],
	FOREIGN KEY (module_ident) REFERENCES modules ON DELETE CASCADE
);

CREATE TABLE "collated_fti" (
	"item" integer,
	"context" integer,
	"module_idx" tsvector,
    "fulltext" text,
    PRIMARY KEY ("item", "context"),
	FOREIGN KEY (item) REFERENCES modules (module_ident) ON DELETE CASCADE,
	FOREIGN KEY (context) REFERENCES modules (module_ident) ON DELETE CASCADE
);

CREATE TABLE "collated_fti_lexemes" (
	"item" integer,
	"context" integer,
	"lexeme" text,
    "positions" int[],
	FOREIGN KEY (item) REFERENCES modules (module_ident) ON DELETE CASCADE,
	FOREIGN KEY (context) REFERENCES modules (module_ident) ON DELETE CASCADE
);

CREATE TABLE "keywords" (
	"keywordid" serial PRIMARY KEY,
	"word" text NOT NULL
);

CREATE TABLE "modulekeywords" (
	"module_ident" integer NOT NULL,
	"keywordid" integer NOT NULL,
	FOREIGN KEY (module_ident) REFERENCES "modules" DEFERRABLE,
	FOREIGN KEY (keywordid) REFERENCES "keywords" DEFERRABLE
);

CREATE TABLE files (
    fileid serial PRIMARY KEY,
    md5 text,
    sha1 text UNIQUE,
    file bytea,
    media_type text
);

CREATE TABLE module_files (
    module_ident integer references modules,
    fileid integer references files,
    filename text
);

CREATE TABLE modulecounts (
	countdate date,
	modcount int);

CREATE TABLE similarities (
	objectid text,
	version text,
	sims text[]
);

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

CREATE TABLE service_states (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  default_priority INTEGER NOT NULL,
  default_message TEXT NOT NULL
);

CREATE TABLE service_state_messages (
  id SERIAL PRIMARY KEY,
  service_state_id INTEGER,
  "starts" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "ends" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '2 hours',
  -- If present, these should take priority over the service_states values.
  priority INTEGER DEFAULT NULL,
  message TEXT DEFAULT NULL,
  FOREIGN KEY (service_state_id) REFERENCES service_states (id)
);

CREATE TABLE collated_file_associations (
  context INTEGER,
  item INTEGER,
  fileid INTEGER,
  FOREIGN KEY (fileid) REFERENCES files (fileid),
  FOREIGN KEY (context) REFERENCES modules (module_ident),
  FOREIGN KEY (item) REFERENCES modules (module_ident),
  -- primary key allows for a single collection and module association
  PRIMARY KEY (context, item)
);
