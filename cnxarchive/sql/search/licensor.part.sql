-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
SELECT
  module_ident,
  %({0})s::text||'-::-licensor' as key
FROM
  latest_modules AS m
  NATURAL JOIN moduleoptionalroles AS mor
  NATURAL JOIN roles AS r,
  users AS u
WHERE
  u.username = any (mor.personids)
  AND
  lower(r.rolename) = 'licensor'
  AND
  (u.first_name ~* req(%({0})s::text)
   OR
   u.last_name ~* req(%({0})s::text)
   OR
   u.full_name ~* req(%({0})s::text)
   OR
   (select bool_or('t')
    from contact_infos as ci
    where ci.user_id = u.id
          AND ci.type = 'EmailAddress'
          AND (ci.value ~* (req(%({0})s::text)||'.*@')
               OR
               (ci.value ~*  (req(%({0})s::text))
                AND
                %({0})s::text  ~ '@'
                )
               )
    )
   )
