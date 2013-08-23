-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string
SELECT filename, mimetype, file
FROM module_files as mf
LEFT JOIN files f on mf.fileid = f.fileid
WHERE mf.uuid = %(id)s;
