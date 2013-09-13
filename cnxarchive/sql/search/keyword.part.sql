SELECT
  cm.module_ident,
  %({0})s::text ||'-::-keyword' as key
FROM
  latest_modules cm,
  modulekeywords mk,
  keywords k
WHERE
  cm.module_ident = mk.module_ident
  AND
  mk.keywordid = k.keywordid
  AND
  k.word ~* req(%({0})s::text)
