-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string
SELECT tree_to_json(moduleid)
FROM modules
WHERE
  uuid = %(id)s
  AND
  version = %(version)s
;
