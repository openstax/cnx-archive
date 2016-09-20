-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: uuid:string; version:string
select is_collated 
FROM trees AS t
  JOIN modules AS m ON t.documentid = m.module_ident
WHERE uuid = %(uuid)s AND module_version(m.major_version,m.minor_version) = %(version)s
ORDER BY is_collated DESC
LIMIT 1;
