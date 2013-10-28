-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

INSERT INTO roles (roleid, roleparam, rolename, roledisplayname, roleattribution, rolecomment)
VALUES (1, 'authors', 'Author', 'Authors', 'Written by:', 'Intellectual author of the work.');
INSERT INTO roles (roleid, roleparam, rolename, roledisplayname, roleattribution, rolecomment)
VALUES (2, 'licensors', 'Licensor', 'Copyright Holders', 'Copyright by:', 'Legal rights holder of the work.');
INSERT INTO roles (roleid, roleparam, rolename, roledisplayname, roleattribution, rolecomment)
VALUES (3, 'maintainers', 'Maintainer', 'Maintainers', 'Maintained by:', 'Has technical permission to republish the work.');
INSERT INTO roles (roleid, roleparam, rolename, roledisplayname, roleattribution, rolecomment)
VALUES (4, 'translators', 'Translator', 'Translators', 'Translation by:', 'Provided language translation.');
INSERT INTO roles (roleid, roleparam, rolename, roledisplayname, roleattribution, rolecomment)
VALUES (5, 'editors', 'Editor', 'Editors', 'Edited by:', 'Provided editorial oversight.');
