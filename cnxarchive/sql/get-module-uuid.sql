-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string
SELECT
uuid
FROM latest_modules m
WHERE short_id(m.uuid) = %(id)s
ORDER BY m.revised DESC
