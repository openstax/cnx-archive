-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
-- arguments connection_options:string, user_mapping_options:string

CREATE EXTENSION postgres_fdw;

CREATE SERVER oscaccounts
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS {connection_options};

CREATE USER MAPPING FOR CURRENT_USER
  SERVER oscaccounts
  OPTIONS {user_mapping_options};

CREATE FOREIGN TABLE users (
  id integer NOT NULL,
  username character varying(255) DEFAULT ''::character varying NOT NULL,
  created_at timestamp without time zone NOT NULL,
  updated_at timestamp without time zone NOT NULL,
  is_administrator boolean DEFAULT false,
  person_id integer,
  is_temp boolean DEFAULT true,
  first_name character varying(255),
  last_name character varying(255),
  full_name character varying(255),
  title character varying(255),
  uuid character varying(255)
  )
  SERVER oscaccounts;

CREATE FOREIGN TABLE contact_infos (
  id integer NOT NULL,
  type character varying(255),
  value character varying(255),
  verified boolean DEFAULT false,
  confirmation_code character varying(255),
  user_id integer,
  created_at timestamp without time zone NOT NULL,
  updated_at timestamp without time zone NOT NULL,
  confirmation_sent_at timestamp without time zone
  )
  SERVER oscaccounts;
