# -*- coding: utf-8 -*-
"""\
- Move the mimetype value from ``module_files`` to ``files``.
- Remove the ``mimetype`` column from the ``module_files`` table.

"""
from __future__ import print_function
import sys


def up(cursor):
    # Move the mimetype value from ``module_files`` to ``files``.
    cursor.execute("UPDATE files AS f SET media_type = mf.mimetype "
                   "FROM module_files AS mf "
                   "WHERE mf.fileid = f.fileid AND f.media_type IS NULL")

    # Warn about missing mimetype.
    cursor.execute("SELECT fileid, sha1 "
                   "FROM files AS f "
                   "WHERE f.fileid NOT IN (SELECT fileid FROM module_files)")
    rows = '\n'.join(['{}, {}'.format(fid, sha1)
                      for fid, sha1 in cursor.fetchall()])
    print("These files (fileid, sha1) do not have a corresponding "
          "module_files entry:\n{}\n".format(rows),
          file=sys.stderr)

    # Remove the ``mimetype`` column from the ``module_files`` table.
    cursor.execute("ALTER TABLE module_files DROP COLUMN mimetype")


def down(cursor):
    # Add a ``mimetype`` column to the ``module_files`` table.
    cursor.execute("ALTER TABLE module_files ADD COLUMN mimetype TEXT")

    # Move the mimetype value from ``files`` to ``module_files``.
    print("Rollback cannot accurately replace mimetype values that "
          "were in the ``modules_files`` table.",
          file=sys.stderr)
    cursor.execute("UPDATE module_files AS mf SET mimetype = f.media_type "
                   "FROM files AS f "
                   "WHERE f.fileid = mf.fileid")
