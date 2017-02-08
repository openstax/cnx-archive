-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: hash:str, id:str, version:str

SELECT mf.filename, f.media_type
FROM
  module_files AS mf
  LEFT JOIN files AS f ON mf.fileid = f.fileid
  LEFT JOIN modules AS m ON mf.module_ident = m.module_ident
WHERE
  m.uuid = %(id)s
  AND module_version( m.major_version, m.minor_version) = %(version)s
  AND f.sha1 = %(hash)s;
