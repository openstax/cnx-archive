CREATE OR REPLACE LANGUAGE plpythonu;

-- tsearch2 is used for fulltext indexing and search
-- It can't be replaced while legacy is still kicking.
CREATE EXTENSION tsearch2;

-- pg_trgm is used for modules name (title) indexing and search.
CREATE EXTENSION pg_trgm;
