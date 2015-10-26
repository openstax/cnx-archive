-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: ident_hash:string, major_version:int, minor_version:int, search_term:string
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder]
FROM 
  trees tr, 
  modules m
WHERE 
  m.uuid::text = %(ident_hash)s AND
  m.major_version = %(major_version)s AND  m.minor_version = %(minor_version)s AND
  tr.documentid = m.module_ident AND
  tr.parent_id IS NULL
UNION ALL
SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder]
FROM trees c1 JOIN t ON (c1.parent_id = t.node)
WHERE NOT nodeid = any (t.path)
)
SELECT
M .uuid,
M .version,
COALESCE(T .title, M . NAME),
ts_headline(
convert_from(f.file, 'utf8'),
plainto_tsquery(%(search_term)s),
'MaxFragments=1'
),
ts_rank_cd(mft.module_idx, plainto_tsquery(%(search_term)s)) AS rank
FROM
t left join  modules m on t.value = m.module_ident join modulefti mft on mft.module_ident = m.module_ident join module_files mf on m.module_ident = mf.module_ident join files f on mf.fileid = f.fileid
WHERE 
mft.module_idx @@ plainto_tsquery(%(search_term)s) 
and mf.filename = 'index.cnxml.html' 
-- this might be a very expensive WHERE clause, leave it out?
and ts_rank_cd(mft.module_idx, plainto_tsquery(%(search_term)s)) > 0.01
ORDER BY 
path
