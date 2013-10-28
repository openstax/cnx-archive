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
  latest_modules m
  NATURAL JOIN moduleoptionalroles mor
  NATURAL JOIN roles r,
  users u
WHERE
  -- FIXME Casting user.id to text. Shouldn't need to do this.
  u.id::text = any (mor.personids)
  AND
  lower(r.rolename) = 'translator'
  AND
  (u.firstname ~* req(%({0})s::text)
   OR
   u.surname ~* req(%({0})s::text)
   OR
   u.fullname ~* req(%({0})s::text)
   OR
   u.email ~* (req(%({0})s::text)||'.*@')
   OR
   (u.email ~* (req(%({0})s::text))
    AND
    %({0})s::text  ~ '@'
    )
   )
