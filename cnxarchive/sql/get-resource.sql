-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: hash:string
SELECT mf.mimetype, f.file
FROM module_files as mf
LEFT JOIN files f on mf.fileid = f.fileid
WHERE f.sha1 = %(hash)s
OR f.md5 = %(hash)s
;
