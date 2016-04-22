# -*- coding: utf-8 -*-
"""\
- Add a ``media_type`` column to the ``files`` table.
- Move the mimetype value from ``module_files`` to ``files``.

"""


def up(cursor):
    # Add a ``media_type`` column to the ``files`` table.
    cursor.execute("ALTER TABLE files ADD COLUMN media_type TEXT")

    # Move the mimetype value from ``module_files`` to ``files``.
    cursor.execute("UPDATE files AS f SET media_type = mf.mimetype "
                   "FROM module_files AS mf "
                   "WHERE mf.fileid = f.fileid")


def down(cursor):
    # Remove the ``mimetype`` column from the ``files`` table.
    cursor.execute("ALTER TABLE files DROP COLUMN media_type")
