-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

CREATE OR REPLACE FUNCTION tree_to_json(uuid TEXT, version TEXT, as_collated BOOLEAN DEFAULT TRUE) RETURNS TEXT as $$
select string_agg(toc,'
'
) from (
WITH RECURSIVE t(node, title, path,value, depth, corder, is_collated) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder],
           is_collated
    FROM trees tr, modules m
    WHERE m.uuid::text = $1 AND
          module_version( m.major_version, m.minor_version) = $2 AND
      tr.documentid = m.module_ident AND
      tr.parent_id IS NULL AND
      tr.is_collated = $3
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder], c1.is_collated /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path) AND t.is_collated = c1.is_collated
)
SELECT
    REPEAT('    ', depth - 1) || 
    '{"id":"' || COALESCE(m.uuid::text,'subcol') || concat_ws('.','@'||m.major_version, m.minor_version) ||'",' ||
    '"shortId":"' || COALESCE(short_id(m.uuid),'subcol') || concat_ws('.','@'||m.major_version, m.minor_version) ||'",' ||
      '"title":'||to_json(COALESCE(title,name))||
      CASE WHEN (depth < lead(depth,1,0) over(w)) THEN ', "contents":['
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) = 0 AND m.uuid IS NULL) THEN ', "contents":[]}'||REPEAT(']}',depth - lead(depth,1,0) over(w) - 1)
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) = 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) over(w) - 1)
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) != 0 AND m.uuid IS NULL) THEN ', "contents":[]}'||REPEAT(']}',depth - lead(depth,1,0) over(w))||','
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) != 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) over(w))||','
           WHEN m.uuid IS NULL THEN ', "contents":[]},'
           ELSE '},' END
      AS "toc"
FROM t left join  modules m on t.value = m.module_ident
    WINDOW w as (ORDER BY corder) order by corder ) tree ;
$$ LANGUAGE SQL;





CREATE OR REPLACE FUNCTION tree_to_json_for_legacy(TEXT, TEXT) RETURNS TEXT AS $$
SELECT string_agg(toc,'
'
) FROM (
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder]
    FROM trees tr, modules m
    WHERE m.uuid::text = $1 AND
          module_version( m.major_version, m.minor_version) = $2 AND
      tr.documentid = m.module_ident AND
      tr.parent_id IS NULL AND
      tr.is_collated = FALSE
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder] /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE NOT nodeid = ANY (t.path) AND c1.is_collated = FALSE
)
SELECT
    REPEAT('    ', depth - 1) || '{"id":"' || COALESCE(m.moduleid,'subcol') ||  '",' ||
      '"version":' || COALESCE('"'||m.version||'"', 'null') || ',' ||
      '"title":'||to_json(COALESCE(title,name))||
      CASE WHEN (depth < lead(depth,1,0) OVER(w)) THEN ', "contents":['
           WHEN (depth > lead(depth,1,0) OVER(w) AND lead(depth,1,0) OVER(w) = 0 AND m.uuid IS NULL) THEN ', "contents":[]}'||REPEAT(']}',depth - lead(depth,1,0) OVER(w) - 1)
           WHEN (depth > lead(depth,1,0) OVER(w) AND lead(depth,1,0) OVER(w) = 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) OVER(w) - 1)
           WHEN (depth > lead(depth,1,0) OVER(w) AND lead(depth,1,0) OVER(w) != 0 AND m.uuid IS NULL) THEN ', "contents":[]}'||REPEAT(']}',depth - lead(depth,1,0) OVER(w))||','
           WHEN (depth > lead(depth,1,0) OVER(w) AND lead(depth,1,0) OVER(w) != 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) OVER(w))||','
           WHEN m.uuid IS NULL THEN ', "contents":[]},'
           ELSE '},' END
      AS "toc"
FROM t LEFT JOIN modules m ON t.value = m.module_ident
    WINDOW w AS (ORDER BY corder) ORDER BY corder ) tree ;
$$ LANGUAGE SQL;
