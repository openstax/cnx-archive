-- arguments: id:string query:string
SELECT
  ts_headline(mfti.fulltext, plainto_tsquery(%(query)s),
              'StartSel=<b>, StopSel=</b>, ShortWord=5, MinWords=50, MaxWords=60') as headline,
  ts_headline(mfti.fulltext, plainto_tsquery(%(query)s),
         'StartSel=<b>, StopSel=</b>, MinWords=600, MaxWords=700') as fulltext
FROM
  latest_modules as lm,
  modulefti as mfti
WHERE
  lm.uuid = %(id)s::uuid
  AND
  NOT lm.portal_type = 'Collection'
  AND
  lm.module_ident = mfti.module_ident
