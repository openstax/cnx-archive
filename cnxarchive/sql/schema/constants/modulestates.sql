INSERT INTO modulestates VALUES (0, 'unknown');
INSERT INTO modulestates VALUES (1, 'current');
INSERT INTO modulestates VALUES (4, 'obsolete');
INSERT INTO modulestates VALUES (5, 'post-publication');
INSERT INTO modulestates VALUES (6, 'processing');
INSERT INTO modulestates VALUES (7, 'errored');

SELECT pg_catalog.setval('modulestates_stateid_seq', 8, false);
