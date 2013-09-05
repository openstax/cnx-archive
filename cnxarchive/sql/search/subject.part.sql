SELECT
  module_ident,
  %({0})s::text ||'-::-subject' as key
FROM
  latest_modules NATURAL JOIN moduletags NATURAL JOIN tags
WHERE
  tag ~* req(%({0})s::text)
