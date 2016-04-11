-- arguments text_terms:string "%(text_terms)s"
SELECT row_to_json(combined_rows) as results
FROM (
WITH weighted_query_results AS (
  SELECT
    module_ident,
    cast(sum(weight) as bigint) as weight,
    semilist(keys) as keys
  FROM
    ({queries}) as matched
  -- table join...
  GROUP BY module_ident

  ),
derived_weighted_query_results AS (
  SELECT
    wqr.module_ident,
    CASE WHEN lm.parent IS NULL THEN weight + 1
         ELSE weight
    END AS weight,
    keys
  FROM weighted_query_results AS wqr
       LEFT JOIN latest_modules AS lm ON (wqr.module_ident = lm.module_ident)
  )
SELECT
  lm.name as title, title_order(lm.name) as "sortTitle",
  lm.uuid as id,
  CASE
    WHEN lm.portal_type = 'Collection'
      THEN lm.major_version || '.' || lm.minor_version
    ELSE lm.major_version || ''
  END AS version,
  language,
  lm.portal_type as "mediaType",
  iso8601(lm.revised) as "pubDate",
  ARRAY(SELECT k.word FROM keywords as k, modulekeywords as mk
        WHERE mk.module_ident = lm.module_ident
              AND mk.keywordid = k.keywordid) as keywords,
  ARRAY(SELECT tags.tag FROM tags, moduletags as mt
        WHERE mt.module_ident = lm.module_ident
              AND mt.tagid = tags.tagid) as subjects,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT username as id,
                first_name as firstname, last_name as surname,
                full_name as fullname, title, suffix
         FROM users
         WHERE users.username::text = ANY (lm.authors)
         ) as user_rows) as authors,
  -- The following are used internally for further sorting and debugging.
  weight, rank,
  keys as _keys, '' as matched, '' as fields,
  ts_headline(ab.html,plainto_tsquery(%(text_terms)s), 'ShortWord=5, MinWords=50, MaxWords=60') as abstract,
  -- until we actually do something with it
  -- ts_headline(mfti.fulltext, plainto_tsquery(%(text_terms)s),
  --            'StartSel=<b>, StopSel=</b>, ShortWord=5, MinWords=50, MaxWords=60') as headline
  NULL as headline
-- Only retrieve the most recent published modules.
FROM
  latest_modules AS lm 
  NATURAL LEFT JOIN abstracts AS ab 
  NATURAL LEFT JOIN modulefti AS mfti
  {limits}
  LEFT OUTER JOIN recent_hit_ranks ON (lm.uuid = document),
  derived_weighted_query_results AS wqr
WHERE
  wqr.module_ident = lm.module_ident
  AND lm.portal_type != 'CompositeModule'
  {filters}
  {groupby}
ORDER BY {sorts}

) as combined_rows
;
