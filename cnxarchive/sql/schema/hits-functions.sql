CREATE OR REPLACE FUNCTION get_recency_date () RETURNS TIMESTAMP
AS $$
  DECLARE
    now_timestamp TIMESTAMP;
    past_timestamp TIMESTAMP;
  BEGIN
    now_timestamp := now();
    past_timestamp := now_timestamp - interval '1 week';
    RETURN past_timestamp;
  END;
$$
LANGUAGE plpgsql;
