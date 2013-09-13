SELECT
  module_ident,
  %({0})s::text||'-::-maintainer' as key
FROM
  latest_modules m,
  users u
WHERE
  -- FIXME Casting user.id to text. Shouldn't need to do this.
  u.id::text = any (m.maintainers)
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
