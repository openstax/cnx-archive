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


CREATE OR REPLACE FUNCTION hit_average (ident INTEGER, recent BOOLEAN)
RETURNS FLOAT
AS $$
  DECLARE
    average FLOAT;
  BEGIN
    recent := coalesce(recent, 'f')::BOOLEAN;
    IF recent THEN
      average := avg(hits) FROM document_hits
        WHERE documentid = ident AND start_timestamp >= get_recency_date();
    ELSE
      average := avg(hits) FROM document_hits WHERE documentid = ident;
    END IF;
    RETURN average;
  END;
$$
LANGUAGE plpgsql;
