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


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: identities; Type: TABLE; Schema: public; Owner: cnxuser; Tablespace: 
--

CREATE TABLE identities (
    id uuid NOT NULL,
    identifier character varying NOT NULL,
    name character varying NOT NULL,
    type character varying NOT NULL,
    profile character varying,
    credentials character varying,
    user_id uuid
);


ALTER TABLE public.identities OWNER TO cnxuser;

--
-- Name: users; Type: TABLE; Schema: public; Owner: cnxuser; Tablespace: 
--

CREATE TABLE users (
    id uuid NOT NULL,
    email character varying,
    firstname character varying,
    othername character varying,
    surname character varying,
    fullname character varying,
    title character varying,
    suffix character varying,
    website character varying,
    _legacy_id character varying
);


ALTER TABLE public.users OWNER TO cnxuser;

--
-- Name: identities_identifier_key; Type: CONSTRAINT; Schema: public; Owner: cnxuser; Tablespace: 
--

ALTER TABLE ONLY identities
    ADD CONSTRAINT identities_identifier_key UNIQUE (identifier);


--
-- Name: identities_pkey; Type: CONSTRAINT; Schema: public; Owner: cnxuser; Tablespace: 
--

ALTER TABLE ONLY identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: users__legacy_id_key; Type: CONSTRAINT; Schema: public; Owner: cnxuser; Tablespace: 
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users__legacy_id_key UNIQUE (_legacy_id);


--
-- Name: users_pkey; Type: CONSTRAINT; Schema: public; Owner: cnxuser; Tablespace: 
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: identities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cnxuser
--

ALTER TABLE ONLY identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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

