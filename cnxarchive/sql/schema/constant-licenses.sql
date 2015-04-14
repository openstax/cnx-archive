-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (0,NULL,NULL,NULL,NULL,'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (1,'by','1.0','Attribution','http://creativecommons.org/licenses/by/1.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (2,'by-nd','1.0','Attribution-NoDerivs','http://creativecommons.org/licenses/by-nd/1.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (3,'by-nd-nc','1.0','Attribution-NoDerivs-NonCommercial','http://creativecommons.org/licenses/by-nd-nc/1.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (4,'by-nc','1.0','Attribution-NonCommercial','http://creativecommons.org/licenses/by-nc/1.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (5,'by-sa','1.0','Attribution-ShareAlike','http://creativecommons.org/licenses/by-sa/1.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (6,'by','2.0','Attribution','http://creativecommons.org/licenses/by/2.0/', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (7,'by-nd','2.0','Attribution-NoDerivs','http://creativecommons.org/licenses/by-nd/2.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (8,'by-nd-nc','2.0','Attribution-NoDerivs-NonCommercial','http://creativecommons.org/licenses/by-nd-nc/2.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (9,'by-nc','2.0','Attribution-NonCommercial','http://creativecommons.org/licenses/by-nc/2.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (10,'by-sa','2.0','Attribution-ShareAlike','http://creativecommons.org/licenses/by-sa/2.0', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (11,'by','3.0','Attribution','http://creativecommons.org/licenses/by/3.0/', 'f');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (12,'by','4.0','Attribution','http://creativecommons.org/licenses/by/4.0/', 't');
INSERT INTO licenses (licenseid, code, "version", name, url, "is_valid_for_publication")
VALUES (13,'by-nc-sa','4.0','Attribution-NonCommercial-ShareAlike','http://creativecommons.org/licenses/by-nc-sa/4.0/', 't');
SELECT pg_catalog.setval('licenses_licenseid_seq', 13, false);
