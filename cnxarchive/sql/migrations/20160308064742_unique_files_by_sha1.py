# -*- coding: utf-8 -*-
"""\
- Migrate all `module_files` records to a single `files` entry.
- Fix the `files` table to only allow one copy of a file.

"""


def up(cursor):
    # Migrate all `module_files` records to a single `files` entry.
    cursor.execute("""\
WITH grouped_files AS (
  SELECT f.sha1, array_agg(f.fileid ORDER BY f.fileid ASC) AS fileids
  FROM files AS f
  WHERE (SELECT DISTINCT count(*) FROM files AS f2 WHERE f.sha1 = f2.sha1) > 1
  GROUP BY f.sha1
),
for_removal AS (
  SELECT unnest(gf.fileids[2:array_length(gf.fileids,1)]) AS fileid
  FROM grouped_files as gf
),
updated_files as (
  UPDATE module_files AS mf
  SET fileid = gf.fileids[1]
  FROM grouped_files AS gf
  WHERE mf.fileid = any(gf.fileids)
  RETURNING mf.fileid
)
DELETE FROM files WHERE fileid IN (SELECT fileid FROM for_removal)
""")
    # Fix the `files` table to only allow one copy of a file.
    cursor.execute("ALTER TABLE files ADD UNIQUE (sha1)")


def down(cursor):
    pass
