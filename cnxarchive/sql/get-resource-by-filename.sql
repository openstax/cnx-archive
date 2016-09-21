-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string; filename:string
SELECT f.file
FROM module_files as mf
  LEFT JOIN files f on mf.fileid = f.fileid
  LEFT JOIN modules m on mf.module_ident = m.module_ident
WHERE m.uuid = %(id)s AND
      module_version(m.major_version, m.minor_version) = %(version)s AND
      mf.filename = %(filename)s;
