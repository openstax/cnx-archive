-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: hash:str

SELECT mf.filename, f.media_type
FROM
  module_files AS mf
  LEFT JOIN files AS f ON mf.fileid = f.fileid
WHERE
  f.sha1 = %(hash)s
