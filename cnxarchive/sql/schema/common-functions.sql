CREATE OR REPLACE FUNCTION iso8601 (dt TIMESTAMP WITH TIME ZONE)
RETURNS TEXT
AS $$
-- Returns a UTC timestamp that can be parsed by all browsers
--   javascript implementations.
  BEGIN
    RETURN replace(date_trunc('second', dt at time zone 'UTC')::text,' ','T')||'Z';
  END;
$$ LANGUAGE plpgsql;
SELECT iso8601(current_timestamp), current_timestamp;

-- Returns arrays in the order they are stored in the database, 
--    based on the index
CREATE OR REPLACE FUNCTION idx(anyarray, anyelement)
  RETURNS INT AS 
$$
  SELECT i FROM (
     SELECT generate_series(array_lower($1,1),array_upper($1,1))
  ) g(i)
  WHERE $1[i] = $2
  LIMIT 1;
$$ LANGUAGE SQL IMMUTABLE;

-- Returns the Python `sys.path`
--   Example usage, `SELECT unnest(pypath())`
CREATE OR REPLACE FUNCTION pypath()
  RETURNS TEXT[]
  AS $$
import sys
return sys.path
$$ LANGUAGE plpythonu;

-- Returns module location for the given module
--   Example usage, `SELECT * FROM pyimport('cnxarchive.database');`
CREATE TYPE pyimport_value AS (
  import TEXT,
  directory TEXT,
  file_path TEXT
);
CREATE OR REPLACE FUNCTION pyimport(pymodule TEXT)
  RETURNS SETOF pyimport_value
  AS $$
import os
import importlib
try:
    module = importlib.import_module(pymodule)
except ImportError:
    return []
file_path = os.path.abspath(module.__file__)
directory = os.path.dirname(file_path)
info = {
    'import': pymodule,
    'directory': directory,
    'file_path': file_path,
}
return [info]
$$ LANGUAGE plpythonu;
