SELECT
  module_ident,
  %({0})s::text||'-::-title' as key
FROM
  latest_modules
WHERE
  name ~* ('(^| )'||req(%({0})s::text)||'( |$)'::text)
