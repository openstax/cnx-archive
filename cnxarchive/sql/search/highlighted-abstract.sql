-- arguments: id:string query:string
SELECT
  ts_headline(abstract, plainto_tsquery(%(query)s),
             'StartSel=<b>, StopSel=</b>, ShortWord=5, MinWords=50, MaxWords=60'
             ) as headline,
  ts_headline(abstract, plainto_tsquery(%(query)s),
             'StartSel=<b>, StopSel=</b>, MinWords=600, MaxWords=700') as abstract
FROM abstracts natural join latest_modules
WHERE uuid = %(id)s::uuid
