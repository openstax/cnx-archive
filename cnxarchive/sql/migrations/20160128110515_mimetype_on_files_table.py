# -*- coding: utf-8 -*-
"""\
- Add a ``media_type`` column to the ``files`` table.
- Move the mimetype value from ``module_files`` to ``files``.

"""
from __future__ import print_function
import sys


def up(cursor):
    # Add a ``media_type`` column to the ``files`` table.
    cursor.execute("ALTER TABLE files ADD COLUMN media_type TEXT")

    # Drop the triggers from the files table
    cursor.execute("DROP TRIGGER update_file_md5 ON files")
    cursor.execute("DROP TRIGGER update_files_sha1 ON files")

    # Move the mimetype value from ``module_files`` to ``files``.
    cursor.execute("UPDATE files AS f SET media_type = mf.mimetype "
                   "FROM module_files AS mf "
                   "WHERE mf.fileid = f.fileid")

    # Put triggers back
    cursor.execute("CREATE TRIGGER update_file_md5 "
                   "BEFORE INSERT OR UPDATE OF file ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_md5()")

    cursor.execute("CREATE TRIGGER update_files_sha1 "
                   "BEFORE INSERT OR UPDATE OF file ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_sha1()")

    # Warn about missing mimetype.
    cursor.execute("SELECT fileid, sha1 "
                   "FROM files AS f "
                   "WHERE f.fileid NOT IN (SELECT fileid FROM module_files)")
    rows = '\n'.join(['{}, {}'.format(fid, sha1)
                      for fid, sha1 in cursor.fetchall()])
    print("These files (fileid, sha1) do not have a corresponding "
          "module_files entry:\n{}\n".format(rows),
          file=sys.stderr)


def down(cursor):
    # Remove the ``mimetype`` column from the ``files`` table.
    cursor.execute("ALTER TABLE files DROP COLUMN media_type")

    # Drop the triggers from the files table
    cursor.execute("DROP TRIGGER update_file_md5 ON files")
    cursor.execute("DROP TRIGGER update_files_sha1 ON files")

    # Put triggers back
    cursor.execute("CREATE TRIGGER update_file_md5 "
                   "BEFORE INSERT OR UPDATE ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_md5()")

    cursor.execute("CREATE TRIGGER update_files_sha1 "
                   "BEFORE INSERT OR UPDATE ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_sha1()")
