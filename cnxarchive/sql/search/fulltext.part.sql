SELECT
  cm.module_ident,
  %({0})s::text ||'-::-fulltext' as key,
  ts_rank_cd('{{1.0,1.0,1.0,1.0}}', module_idx, plainto_tsquery(%({0})s),4) * 2 ^ length(to_tsvector(%({0})s)) as rank
FROM
  latest_modules cm,
  modulefti mf
WHERE
  cm.module_ident = mf.module_ident
  AND
  module_idx @@ plainto_tsquery(%({0})s)
