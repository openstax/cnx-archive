-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

CREATE OR REPLACE FUNCTION get_recency_date () RETURNS TIMESTAMP
AS $$
  DECLARE
    now_timestamp TIMESTAMP WITH TIME ZONE;
    past_timestamp TIMESTAMP WITH TIME ZONE;
  BEGIN
    now_timestamp := COALESCE(MAX(end_timestamp), NOW()) FROM document_hits;
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

CREATE OR REPLACE FUNCTION update_hit_ranks () RETURNS VOID
AS $$
  BEGIN
    DELETE FROM recent_hit_ranks;
    DELETE FROM overall_hit_ranks;
    -- Inserted new records are grouped by uuid.

    -- Inserts into the recent_hit_ranks table
    WITH
      ident_mapping AS
      (SELECT uuid, array_agg(module_ident) AS idents
       FROM modules GROUP BY uuid),
      stats AS
      (SELECT im.uuid AS document,
              sum(hits) AS hits,
              avg(hits) AS average,
              rank() OVER (ORDER BY avg(hits)) as rank
       FROM ident_mapping AS im,
            document_hits AS dh
       WHERE dh.documentid = any(im.idents)
             AND start_timestamp >= get_recency_date()
       GROUP BY im.uuid)
    INSERT INTO recent_hit_ranks select * from stats;

    -- Inserts into the overall_hit_ranks table.
    WITH
      ident_mapping AS
      (SELECT uuid, array_agg(module_ident) AS idents
       FROM modules GROUP BY uuid),
      stats AS
      (SELECT im.uuid AS document,
              sum(hits) AS hits,
              avg(hits) AS average,
              rank() OVER (ORDER BY avg(hits)) AS rank
       FROM ident_mapping AS im,
            document_hits AS dh
       WHERE dh.documentid = any(im.idents)
       GROUP BY im.uuid)
    INSERT INTO overall_hit_ranks select * from stats;

  END;
$$
LANGUAGE plpgsql;
