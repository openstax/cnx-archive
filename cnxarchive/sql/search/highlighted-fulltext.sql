-- arguments: id:string query:string
SELECT
  ts_headline(convert_from(f.file, 'UTF8'), plainto_tsquery(%(query)s),
              'StartSel=<b>, StopSel=</b>, ShortWord=5, MinWords=50, MaxWords=60') as headline,
  ts_headline(convert_from(f.file, 'UTF8'), plainto_tsquery(%(query)s),
         'StartSel=<b>, StopSel=</b>, MinWords=600, MaxWords=700') as fulltext
FROM
  latest_modules as lm,
  module_files as mf,
  files as f
WHERE
  lm.uuid = %(id)s::uuid
  AND
  ((lm.portal_type = 'Collection' AND mf.filename = 'collection.html')
   OR
   (lm.portal_type = 'Module' AND mf.filename = 'index.html')
   )
  AND
  mf.fileid = f.fileid
