SELECT
  module_ident,
  %({0})s::text ||'-::-parentAuthor' as key
FROM
  latest_modules
WHERE
  %({0})s = any (parentAuthors)
