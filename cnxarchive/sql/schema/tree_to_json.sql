CREATE OR REPLACE FUNCTION tree_to_json(TEXT) RETURNS TEXT as $$
select string_agg(toc,'
'
) from (
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder] 
    FROM trees tr, latest_modules lm
    WHERE moduleid = $1 and tr.documentid = lm.module_ident
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder] /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path)
)
SELECT
    REPEAT('    ', depth - 1) || '{"id":"' || COALESCE(lm.uuid,'subcol') ||COALESCE('@'||lm.version,'') ||'",' ||
      '"title":"'||COALESCE(title,name)||'"' ||
      CASE WHEN (depth < lead(depth,1,0) over(w)) THEN ', "contents":[' 
           WHEN (depth > lead(depth,1,0) over(w) AND depth > 2 ) THEN '}]},' 
           WHEN (depth > lead(depth,1,0) over(w) AND depth = 2 ) THEN '}]}' 
           ELSE '},' END 
      AS "toc" 
FROM t left join  modules lm on t.value = lm.module_ident 
    WINDOW w as (ORDER BY corder) order by corder ) tree ;
$$ LANGUAGE SQL;
