-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: hash:str

SELECT sha1, media_type
FROM
  files 
WHERE
  sha1 = %(hash)s
