INSERT into modulestates (stateid, statename) VALUES(1,'current');

SELECT pg_catalog.setval('modulestates_stateid_seq', 1, false);
