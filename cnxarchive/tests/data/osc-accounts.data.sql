--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: pumazi
--

INSERT INTO users VALUES (1, 'cnxcap', '2014-09-15 12:03:12.549409', '2014-09-15 12:03:12.549409', false, NULL, true, 'College', 'Physics', 'OSC Physics Maintainer', NULL, '1df3bab1-1dc7-4017-9b3a-960a87e706b1');
INSERT INTO users VALUES (2, 'OpenStaxCollege', '2014-09-15 12:04:52.119092', '2014-09-15 12:04:52.119092', false, NULL, true, 'OpenStax College', NULL, 'OpenStax College', NULL, 'e5a07af6-09b9-4b74-aa7a-b7510bee90b8');
INSERT INTO users VALUES (3, 'OSCRiceUniversity', '2014-09-15 12:05:58.558116', '2014-09-15 12:05:58.558116', false, NULL, true, 'Rice', 'University', 'Rice University', NULL, '9366c786-e3c8-4960-83d4-aec1269ac5e5');
INSERT INTO users VALUES (4, 'typo', '2014-09-15 12:03:12.549409', '2014-09-15 12:03:12.549409', false, NULL, true, 'Typo', NULL, 'Typo Error', NULL, '46cf263d-2eef-42f1-8523-1b650006868a');
INSERT INTO users VALUES (5, 'Rasmus1975', '2014-09-15 12:03:12.549409', '2014-09-15 12:03:12.549409', false, NULL, true, 'Rasmus', NULL, 'Rasmus de 1975', NULL, '5b203335-b427-4145-995c-fbd6fd7618c6');

SELECT pg_catalog.setval('users_id_seq', 5, true);

--
-- Data for Name: contact_infos; Type: TABLE DATA; Schema: public; Owner: pumazi
--

INSERT INTO contact_infos VALUES (1, 'EmailAddress', 'info@openstaxcollege.org', true, NULL, 1, '2014-09-15 12:09:09.042549', '2014-09-15 12:09:09.042549', NULL);
INSERT INTO contact_infos VALUES (2, 'EmailAddress', 'info@openstaxcollege.org', true, NULL, 2, '2014-09-15 12:09:34.248854', '2014-09-15 12:09:34.248854', NULL);
INSERT INTO contact_infos VALUES (3, 'EmailAddress', 'daniel@openstaxcollege.org', true, NULL, 3, '2014-09-15 12:10:08.110819', '2014-09-15 12:10:08.110819', NULL);
INSERT INTO contact_infos VALUES (4, 'EmailAddress', 'typo@example.org', true, NULL, 4, '2014-09-15 12:10:08.110819', '2014-09-15 12:10:08.110819', NULL);
INSERT INTO contact_infos VALUES (5, 'EmailAddress', 'rasmus@example.org', true, NULL, 5, '2014-09-15 12:10:08.110819', '2014-09-15 12:10:08.110819', NULL);

SELECT pg_catalog.setval('contact_infos_id_seq', 5, true);
