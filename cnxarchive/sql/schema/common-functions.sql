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