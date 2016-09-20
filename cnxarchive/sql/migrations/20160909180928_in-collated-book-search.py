# -*- coding: utf-8 -*-


def up(cursor):
    # Create collated fulltext tables, parallel to module tables, with an extra 'context' param.

    # Create tables, index functions, and indexes
    cursor.execute("""
CREATE TABLE collated_fti_lexemes (
    item integer,
    context integer,
    lexeme text,
    positions integer[]);

CREATE TABLE collated_fti (
    item integer NOT NULL,
    context integer NOT NULL,
    module_idx pg_catalog.tsvector,
    fulltext text);

ALTER TABLE collated_fti ADD CONSTRAINT collated_fti_pkey PRIMARY KEY (item, context);
ALTER TABLE collated_fti ADD CONSTRAINT collated_fti_context_fkey FOREIGN KEY (context) REFERENCES modules (module_ident) ON DELETE CASCADE;
ALTER TABLE collated_fti ADD CONSTRAINT collated_fti_item_fkey FOREIGN KEY (item) REFERENCES modules (module_ident) ON DELETE CASCADE;

ALTER TABLE collated_fti_lexemes ADD CONSTRAINT collated_fti_lexemes_item_fkey FOREIGN KEY (item) REFERENCES modules (module_ident) ON DELETE CASCADE;
ALTER TABLE collated_fti_lexemes ADD CONSTRAINT collated_fti_lexemes_context_fkey FOREIGN KEY (context) REFERENCES modules (module_ident) ON DELETE CASCADE;

CREATE FUNCTION module_version(major integer, minor integer) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
  SELECT concat_ws('.', major, minor) ;
$_$;

CREATE INDEX collated_fti_idx ON collated_fti USING gist (module_idx);

CREATE INDEX trees_doc_idx ON trees (documentid);

CREATE INDEX modules_uuid_version_idx ON modules (uuid, module_version(major_version, minor_version));

CREATE INDEX latest_modules_uuid_version_idx ON latest_modules (uuid, module_version(major_version, minor_version));

CREATE FUNCTION count_collated_lexemes(myident integer, bookident integer, mysearch text) RETURNS bigint
    LANGUAGE sql STABLE
    AS $_$
     select sum(array_length(positions,1))
            from collated_fti_lexemes,
                 regexp_split_to_table(strip(to_tsvector(mysearch))::text,' ') s
            where item = myident and context = bookident and lexeme = substr(s,2,length(s)-2)
$_$;
""")
    # Update json tree functions to use new module_version function (and perhaps the index)
    cursor.execute("""
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
""")
    # Trigger functions
    cursor.execute("""
CREATE FUNCTION index_collated_fulltext_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT item, context FROM collated_fti WHERE item = NEW.item and context = NEW.context);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO collated_fti (item, context, fulltext, module_idx)
        VALUES ( NEW.item, NEW.context,_baretext, _idx_vectors );
    ELSE
      UPDATE collated_fti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE item = NEW.item and context = NEW.context;
    END IF;
    RETURN NEW;
  END;
$_$;

CREATE FUNCTION index_collated_fulltext_lexeme_update_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
  BEGIN

    DELETE from collated_fti_lexemes where item = NEW.item;

    INSERT into collated_fti_lexemes (item, context, lexeme, positions)
       (with lex as (SELECT regexp_split_to_table(NEW.module_idx::text, E' \\'') as t )
       SELECT NEW.item, NEW.context,
              substring(t,1,strpos(t,E'\\':')-1),
              ('{'||substring(t,strpos(t,E'\\':')+2)||'}')::int[] from lex) ;

  RETURN NEW;
  END;
$_$;
""")
    # and the triggers
    cursor.execute("""
CREATE TRIGGER index_collated_fulltext
    AFTER INSERT OR UPDATE ON collated_file_associations
    FOR EACH ROW
    EXECUTE PROCEDURE index_collated_fulltext_trigger();

CREATE TRIGGER index_collated_fulltext_lexeme
    BEFORE INSERT OR UPDATE ON collated_fti
    FOR EACH ROW
    EXECUTE PROCEDURE index_collated_fulltext_lexeme_update_trigger();
""")

    # Clean up redundant lexeme triggers
    cursor.execute("""
DROP TRIGGER index_fulltext_lexeme ON modulefti;

CREATE TRIGGER index_fulltext_lexeme
    BEFORE INSERT OR UPDATE ON modulefti
    FOR EACH ROW
    EXECUTE PROCEDURE index_fulltext_lexeme_update_trigger();

DROP TRIGGER index_fulltext_lexeme_update ON modulefti;

DROP FUNCTION index_fulltext_lexeme_trigger();
""")

    # Fill tables
    cursor.execute("""
INSERT INTO collated_fti (item, context, fulltext, module_idx)
    SELECT item, context,
    xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text,
    to_tsvector(xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text)
    FROM files AS f, collated_file_associations AS cfa
    WHERE f.fileid = cfa.fileid
""")


def down(cursor):

    cursor.execute("""
CREATE FUNCTION index_fulltext_lexeme_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
  BEGIN

    INSERT into modulefti_lexemes (module_ident, lexeme, positions)
        (with lex as (SELECT regexp_split_to_table(NEW.module_idx::text, E' \\'') as t )
        SELECT NEW.module_ident,
               substring(t,1,strpos(t,E'\\':')-1),
               ('{'||substring(t,strpos(t,E'\\':')+2)||'}')::int[] from lex) ;

  RETURN NEW;
  END;
$_$;

CREATE TRIGGER index_fulltext_lexeme_update
    BEFORE UPDATE ON modulefti
    FOR EACH ROW
    EXECUTE PROCEDURE index_fulltext_lexeme_update_trigger();

DROP TRIGGER index_fulltext_lexeme ON modulefti;

CREATE TRIGGER index_fulltext_lexeme
    BEFORE INSERT ON modulefti
    FOR EACH ROW
    EXECUTE PROCEDURE index_fulltext_lexeme_trigger();
    """)

    cursor.execute("""
CREATE OR REPLACE FUNCTION tree_to_json(uuid TEXT, version TEXT, as_collated BOOLEAN DEFAULT TRUE) RETURNS TEXT as $$
select string_agg(toc,'
'
) from (
WITH RECURSIVE t(node, title, path,value, depth, corder, is_collated) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder],
           is_collated
    FROM trees tr, modules m
    WHERE m.uuid::text = $1 AND
          concat_ws('.', m.major_version, m.minor_version) = $2 AND
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
    '{"id":"' || COALESCE(m.uuid::text,'subcol') ||concat_ws('.', '@'||m.major_version, m.minor_version) ||'",' ||
    '"shortId":"' || COALESCE(short_id(m.uuid),'subcol') ||concat_ws('.', '@'||m.major_version, m.minor_version) ||'",' ||
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
          concat_ws('.',  m.major_version, m.minor_version) = $2 AND
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
""")

    cursor.execute("""
DROP TABLE collated_fti_lexemes;

DROP TABLE collated_fti;

DROP TRIGGER index_collated_fulltext ON collated_file_associations;

DROP FUNCTION index_collated_fulltext_trigger();

DROP FUNCTION index_collated_fulltext_lexeme_update_trigger();

DROP FUNCTION count_collated_lexemes(myident integer, bookident integer, mysearch text);

DROP INDEX trees_doc_idx;

DROP INDEX modules_uuid_version_idx;

DROP INDEX latest_modules_uuid_version_idx;

DROP FUNCTION module_version(major integer, minor integer);
""")
