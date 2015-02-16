-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
SELECT
  module_ident,
  %({0})s::text||'-::-translator' as key
FROM
  latest_modules AS m
  NATURAL JOIN moduleoptionalroles AS mor
  NATURAL JOIN roles AS r,
  users AS u
WHERE
  u.username = ANY (mor.personids)
  AND
  lower(r.rolename) = 'translator'
  AND
  (u.first_name ~* req(%({0})s::text)
   OR
   u.last_name ~* req(%({0})s::text)
   OR
   u.full_name ~* req(%({0})s::text)
   OR
   u.username ~* req(%({0})s::text)
   )
