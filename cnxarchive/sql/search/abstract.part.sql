SELECT
  cm.module_ident,
  %({0})s::text ||'-::-abstract' as key
FROM
  latest_modules cm,
  abstracts a
WHERE
  cm.abstractid = a.abstractid
  AND
  a.abstract ~* req(%({0})s::text)
