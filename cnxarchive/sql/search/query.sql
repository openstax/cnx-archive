SELECT
  lm.name as title, title_order(lm.name) as "sortTitle",
  lm.uuid as id, lm.version as version, language,
  weight, keys as _keys, '' as matched, '' as fields,
  lm.portal_type as "mediaType"
-- Only retrieve the most recent published modules.
FROM
  latest_modules lm,
  (SELECT
     module_ident,
     cast (sum(weight) as bigint) as weight,
     semilist(keys) as keys
   FROM
     ({}) as matched
   GROUP BY module_ident
   ) as weighted
WHERE
  weighted.module_ident = lm.module_ident
  {}
ORDER BY weight DESC
;
