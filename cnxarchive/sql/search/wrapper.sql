SELECT
  module_ident,
  count(*)*{0} as weight,
  semilist(key) as keys
FROM (
  {1}
) cm
GROUP BY cm.module_ident
