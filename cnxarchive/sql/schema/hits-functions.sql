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


CREATE OR REPLACE FUNCTION hit_rank(ident INTEGER, recent BOOLEAN)
RETURNS FLOAT
AS $$
  DECLARE
    document_rank FLOAT;
  BEGIN
    recent := coalesce(recent, 'f')::BOOLEAN;
    IF recent THEN
      WITH ranked_documents AS
        (SELECT documentid, avg(hits) AS hits,
           rank() OVER (ORDER BY avg(hits)) AS rank
         FROM document_hits
         WHERE start_timestamp >= get_recency_date()
         GROUP BY documentid ORDER BY hits DESC)
      SELECT rank
      FROM ranked_documents AS rkd
      WHERE documentid = ident
      INTO document_rank;
    ELSE
      WITH ranked_documents AS
        (SELECT documentid, avg(hits) AS hits,
           rank() OVER (ORDER BY avg(hits)) AS rank
         FROM document_hits
         GROUP BY documentid ORDER BY hits DESC)
      SELECT rank
      FROM ranked_documents AS rkd
      WHERE documentid = ident
      INTO document_rank;
    END IF;
    RETURN document_rank;
  END;
$$
LANGUAGE plpgsql;
