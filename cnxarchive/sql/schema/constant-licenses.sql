-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (0,NULL,NULL,NULL,NULL);
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (1,'by','1.0','Attribution','http://creativecommons.org/licenses/by/1.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (2,'by-nd','1.0','Attribution-NoDerivs','http://creativecommons.org/licenses/by-nd/1.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (3,'by-nd-nc','1.0','Attribution-NoDerivs-NonCommercial','http://creativecommons.org/licenses/by-nd-nc/1.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (4,'by-nc','1.0','Attribution-NonCommercial','http://creativecommons.org/licenses/by-nc/1.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (5,'by-sa','1.0','Attribution-ShareAlike','http://creativecommons.org/licenses/by-sa/1.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (6,'by','2.0','Attribution','http://creativecommons.org/licenses/by/2.0/');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (7,'by-nd','2.0','Attribution-NoDerivs','http://creativecommons.org/licenses/by-nd/2.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (8,'by-nd-nc','2.0','Attribution-NoDerivs-NonCommercial','http://creativecommons.org/licenses/by-nd-nc/2.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (9,'by-nc','2.0','Attribution-NonCommercial','http://creativecommons.org/licenses/by-nc/2.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (10,'by-sa','2.0','Attribution-ShareAlike','http://creativecommons.org/licenses/by-sa/2.0');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (11,'by','3.0','Attribution','http://creativecommons.org/licenses/by/3.0/');
INSERT INTO licenses (licenseid, code, "version", name, url)
VALUES (12,'by','4.0','Attribution','http://creativecommons.org/licenses/by/4.0/');
SELECT pg_catalog.setval('licenses_licenseid_seq', 12, false);
