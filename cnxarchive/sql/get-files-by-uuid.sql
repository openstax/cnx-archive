-- ###
-- Copyright (c) 2015, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: uuid:string
SELECT mf.filename, f.file
FROM
	module_files AS mf
	LEFT JOIN files f ON mf.fileid = f.fileid
	LEFT JOIN modules m ON mf.module_ident = m.module_ident
WHERE
	m.moduleid = %(uuid)s
