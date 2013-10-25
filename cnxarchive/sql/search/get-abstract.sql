-- arguments: id:string query:string
SELECT
  ts_headline(abstract, '', 'ShortWord=5, MinWords=50, MaxWords=60') as headline
FROM abstracts natural join latest_modules
WHERE uuid = %(id)s::uuid
