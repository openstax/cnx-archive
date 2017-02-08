-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! argsf:: id:str, version:str

SELECT m.portal_type
FROM
  modules AS m
WHERE
  m.uuid = %(id)s
  AND module_version( m.major_version, m.minor_version) = %(version)s;
