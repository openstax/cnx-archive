SELECT row_to_json(combined_rows) as results
FROM (

SELECT
  lm.name as title, title_order(lm.name) as "sortTitle",
  lm.uuid as id, lm.version as version, language,
  weight, keys as _keys, '' as matched, '' as fields,
  lm.portal_type as "mediaType",
  lm.created as "pubDate",
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT id, email, firstname, othername, surname, fullname,
                title, suffix, website
         FROM users
         WHERE users.id::text = ANY (lm.authors)
         ) as user_rows) as authors,
  a.abstract as abstract
-- Only retrieve the most recent published modules.
FROM
  latest_modules lm
    LEFT JOIN abstracts a on lm.abstractid = a.abstractid,
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
ORDER BY {}

) as combined_rows
;
