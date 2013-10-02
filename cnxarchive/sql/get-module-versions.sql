-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string
SELECT
  CASE
    WHEN m.portal_type = 'Collection'
      THEN m.major_version || '.' || m.minor_version
    ELSE m.major_version || ''
  END AS version
FROM modules m
WHERE m.uuid = %(id)s
ORDER BY m.module_ident DESC
