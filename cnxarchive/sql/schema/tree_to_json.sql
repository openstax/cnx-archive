CREATE OR REPLACE FUNCTION tree_to_json(TEXT, TEXT) RETURNS TEXT as $$
select string_agg(toc,'
'
) from (
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder]
    FROM trees tr, modules m
    WHERE m.uuid::text = $1 AND m.version = $2 AND tr.documentid = m.module_ident
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder] /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path)
)
SELECT
    REPEAT('    ', depth - 1) || '{"id":"' || COALESCE(m.uuid::text,'subcol') ||COALESCE('@'||m.version,'') ||'",' ||
      '"title":"'||ascii(COALESCE(title,name))||'"' ||
      CASE WHEN (depth < lead(depth,1,0) over(w)) THEN ', "contents":['
           WHEN (depth > lead(depth,1,0) over(w) AND depth > 2 ) THEN '}]},'
           WHEN (depth > lead(depth,1,0) over(w) AND depth = 2 ) THEN '}]}'
           ELSE '},' END
      AS "toc"
FROM t left join  modules m on t.value = m.module_ident
    WINDOW w as (ORDER BY corder) order by corder ) tree ;
$$ LANGUAGE SQL;
