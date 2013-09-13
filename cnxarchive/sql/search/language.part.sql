SELECT
  module_ident,
  %({0})s::text ||'-::-language' as key
FROM
  latest_modules
WHERE
  language ~ ('^'||req(%({0})s::text))
