CREATE EXTENSION IF NOT EXISTS plpythonu;

-- tsearch2 is used for fulltext indexing and search
-- It can't be replaced while legacy is still kicking.
CREATE EXTENSION tsearch2;
