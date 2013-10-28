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
