-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

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

--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;
