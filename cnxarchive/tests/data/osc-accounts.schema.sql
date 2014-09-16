--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: authentications; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE authentications (
    id integer NOT NULL,
    user_id integer,
    provider character varying(255),
    uid character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.authentications OWNER TO accounts;

--
-- Name: authentications_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE authentications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.authentications_id_seq OWNER TO accounts;

--
-- Name: authentications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE authentications_id_seq OWNED BY authentications.id;


--
-- Name: contact_infos; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE contact_infos (
    id integer NOT NULL,
    type character varying(255),
    value character varying(255),
    verified boolean DEFAULT false,
    confirmation_code character varying(255),
    user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    confirmation_sent_at timestamp without time zone
);


ALTER TABLE public.contact_infos OWNER TO accounts;

--
-- Name: contact_infos_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE contact_infos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contact_infos_id_seq OWNER TO accounts;

--
-- Name: contact_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE contact_infos_id_seq OWNED BY contact_infos.id;


--
-- Name: delayed_jobs; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE delayed_jobs (
    id integer NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    handler text NOT NULL,
    last_error text,
    run_at timestamp without time zone,
    locked_at timestamp without time zone,
    failed_at timestamp without time zone,
    locked_by character varying(255),
    queue character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.delayed_jobs OWNER TO accounts;

--
-- Name: delayed_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE delayed_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.delayed_jobs_id_seq OWNER TO accounts;

--
-- Name: delayed_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE delayed_jobs_id_seq OWNED BY delayed_jobs.id;


--
-- Name: fine_print_contracts; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE fine_print_contracts (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    version integer,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.fine_print_contracts OWNER TO accounts;

--
-- Name: fine_print_contracts_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE fine_print_contracts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.fine_print_contracts_id_seq OWNER TO accounts;

--
-- Name: fine_print_contracts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE fine_print_contracts_id_seq OWNED BY fine_print_contracts.id;


--
-- Name: fine_print_signatures; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE fine_print_signatures (
    id integer NOT NULL,
    contract_id integer NOT NULL,
    user_id integer NOT NULL,
    user_type character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.fine_print_signatures OWNER TO accounts;

--
-- Name: fine_print_signatures_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE fine_print_signatures_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.fine_print_signatures_id_seq OWNER TO accounts;

--
-- Name: fine_print_signatures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE fine_print_signatures_id_seq OWNED BY fine_print_signatures.id;


--
-- Name: identities; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE identities (
    id integer NOT NULL,
    password_digest character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    user_id integer NOT NULL,
    reset_code character varying(255),
    reset_code_expires_at timestamp without time zone,
    password_expires_at timestamp without time zone
);


ALTER TABLE public.identities OWNER TO accounts;

--
-- Name: identities_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE identities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.identities_id_seq OWNER TO accounts;

--
-- Name: identities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE identities_id_seq OWNED BY identities.id;


--
-- Name: oauth_access_grants; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE oauth_access_grants (
    id integer NOT NULL,
    resource_owner_id integer NOT NULL,
    application_id integer NOT NULL,
    token character varying(255) NOT NULL,
    expires_in integer NOT NULL,
    redirect_uri character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    revoked_at timestamp without time zone,
    scopes character varying(255)
);


ALTER TABLE public.oauth_access_grants OWNER TO accounts;

--
-- Name: oauth_access_grants_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE oauth_access_grants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth_access_grants_id_seq OWNER TO accounts;

--
-- Name: oauth_access_grants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE oauth_access_grants_id_seq OWNED BY oauth_access_grants.id;


--
-- Name: oauth_access_tokens; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE oauth_access_tokens (
    id integer NOT NULL,
    resource_owner_id integer,
    application_id integer NOT NULL,
    token character varying(255) NOT NULL,
    refresh_token character varying(255),
    expires_in integer,
    revoked_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    scopes character varying(255)
);


ALTER TABLE public.oauth_access_tokens OWNER TO accounts;

--
-- Name: oauth_access_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE oauth_access_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth_access_tokens_id_seq OWNER TO accounts;

--
-- Name: oauth_access_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE oauth_access_tokens_id_seq OWNED BY oauth_access_tokens.id;


--
-- Name: oauth_applications; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE oauth_applications (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    uid character varying(255) NOT NULL,
    secret character varying(255) NOT NULL,
    redirect_uri character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    trusted boolean DEFAULT false,
    owner_id integer,
    owner_type character varying(255)
);


ALTER TABLE public.oauth_applications OWNER TO accounts;

--
-- Name: oauth_applications_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE oauth_applications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth_applications_id_seq OWNER TO accounts;

--
-- Name: oauth_applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE oauth_applications_id_seq OWNED BY oauth_applications.id;


--
-- Name: people; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE people (
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.people OWNER TO accounts;

--
-- Name: people_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE people_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.people_id_seq OWNER TO accounts;

--
-- Name: people_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE people_id_seq OWNED BY people.id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE schema_migrations (
    version character varying(255) NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO accounts;

--
-- Name: users; Type: TABLE; Schema: public; Owner: accounts; Tablespace: 
--

CREATE TABLE users (
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
);


ALTER TABLE public.users OWNER TO accounts;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: accounts
--

CREATE SEQUENCE users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO accounts;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: accounts
--

ALTER SEQUENCE users_id_seq OWNED BY users.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY authentications ALTER COLUMN id SET DEFAULT nextval('authentications_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY contact_infos ALTER COLUMN id SET DEFAULT nextval('contact_infos_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY delayed_jobs ALTER COLUMN id SET DEFAULT nextval('delayed_jobs_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY fine_print_contracts ALTER COLUMN id SET DEFAULT nextval('fine_print_contracts_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY fine_print_signatures ALTER COLUMN id SET DEFAULT nextval('fine_print_signatures_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY identities ALTER COLUMN id SET DEFAULT nextval('identities_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY oauth_access_grants ALTER COLUMN id SET DEFAULT nextval('oauth_access_grants_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY oauth_access_tokens ALTER COLUMN id SET DEFAULT nextval('oauth_access_tokens_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY oauth_applications ALTER COLUMN id SET DEFAULT nextval('oauth_applications_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY people ALTER COLUMN id SET DEFAULT nextval('people_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: accounts
--

ALTER TABLE ONLY users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass);


--
-- Name: authentications_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY authentications
    ADD CONSTRAINT authentications_pkey PRIMARY KEY (id);


--
-- Name: contact_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY contact_infos
    ADD CONSTRAINT contact_infos_pkey PRIMARY KEY (id);


--
-- Name: delayed_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY delayed_jobs
    ADD CONSTRAINT delayed_jobs_pkey PRIMARY KEY (id);


--
-- Name: fine_print_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY fine_print_contracts
    ADD CONSTRAINT fine_print_contracts_pkey PRIMARY KEY (id);


--
-- Name: fine_print_signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY fine_print_signatures
    ADD CONSTRAINT fine_print_signatures_pkey PRIMARY KEY (id);


--
-- Name: identities_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: oauth_access_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY oauth_access_grants
    ADD CONSTRAINT oauth_access_grants_pkey PRIMARY KEY (id);


--
-- Name: oauth_access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY oauth_access_tokens
    ADD CONSTRAINT oauth_access_tokens_pkey PRIMARY KEY (id);


--
-- Name: oauth_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY oauth_applications
    ADD CONSTRAINT oauth_applications_pkey PRIMARY KEY (id);


--
-- Name: people_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY people
    ADD CONSTRAINT people_pkey PRIMARY KEY (id);


--
-- Name: users_pkey; Type: CONSTRAINT; Schema: public; Owner: accounts; Tablespace: 
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: delayed_jobs_priority; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX delayed_jobs_priority ON delayed_jobs USING btree (priority, run_at);


--
-- Name: index_authentications_on_user_id_scoped; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_authentications_on_user_id_scoped ON authentications USING btree (user_id, provider);


--
-- Name: index_contact_infos_on_confirmation_code; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_contact_infos_on_confirmation_code ON contact_infos USING btree (confirmation_code);


--
-- Name: index_contact_infos_on_user_id; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX index_contact_infos_on_user_id ON contact_infos USING btree (user_id);


--
-- Name: index_contact_infos_on_value_user_id_type; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_contact_infos_on_value_user_id_type ON contact_infos USING btree (value, user_id, type);


--
-- Name: index_fine_print_contracts_on_name_and_version; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_fine_print_contracts_on_name_and_version ON fine_print_contracts USING btree (name, version);


--
-- Name: index_fine_print_s_on_u_id_and_u_type_and_c_id; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_fine_print_s_on_u_id_and_u_type_and_c_id ON fine_print_signatures USING btree (user_id, user_type, contract_id);


--
-- Name: index_fine_print_signatures_on_contract_id; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX index_fine_print_signatures_on_contract_id ON fine_print_signatures USING btree (contract_id);


--
-- Name: index_identities_on_user_id; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX index_identities_on_user_id ON identities USING btree (user_id);


--
-- Name: index_oauth_access_grants_on_token; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_oauth_access_grants_on_token ON oauth_access_grants USING btree (token);


--
-- Name: index_oauth_access_tokens_on_refresh_token; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_oauth_access_tokens_on_refresh_token ON oauth_access_tokens USING btree (refresh_token);


--
-- Name: index_oauth_access_tokens_on_resource_owner_id; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX index_oauth_access_tokens_on_resource_owner_id ON oauth_access_tokens USING btree (resource_owner_id);


--
-- Name: index_oauth_access_tokens_on_token; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_oauth_access_tokens_on_token ON oauth_access_tokens USING btree (token);


--
-- Name: index_oauth_applications_on_owner_id_and_owner_type; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE INDEX index_oauth_applications_on_owner_id_and_owner_type ON oauth_applications USING btree (owner_id, owner_type);


--
-- Name: index_oauth_applications_on_uid; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_oauth_applications_on_uid ON oauth_applications USING btree (uid);


--
-- Name: index_users_on_username; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_users_on_username ON users USING btree (username);


--
-- Name: index_users_on_uuid; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX index_users_on_uuid ON users USING btree (uuid);


--
-- Name: unique_schema_migrations; Type: INDEX; Schema: public; Owner: accounts; Tablespace: 
--

CREATE UNIQUE INDEX unique_schema_migrations ON schema_migrations USING btree (version);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

