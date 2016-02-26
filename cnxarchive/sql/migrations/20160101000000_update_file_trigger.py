# -*- coding: utf-8 -*-
"""\
Change file hash update triggers to only trigger on file update
"""


def up(cursor):
    # Drop the triggers from the files table
    cursor.execute("DROP TRIGGER update_file_md5 ON files")
    cursor.execute("DROP TRIGGER update_files_sha1 ON files")

    # Create triggers that run only on file update
    cursor.execute("CREATE TRIGGER update_file_md5 "
                   "BEFORE INSERT OR UPDATE OF file ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_md5()")

    cursor.execute("CREATE TRIGGER update_files_sha1 "
                   "BEFORE INSERT OR UPDATE OF file ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_sha1()")


def down(cursor):
    # Drop the triggers from the files table
    cursor.execute("DROP TRIGGER update_file_md5 ON files")
    cursor.execute("DROP TRIGGER update_files_sha1 ON files")

    # Create triggers that run every time the files table is updated
    cursor.execute("CREATE TRIGGER update_file_md5 "
                   "BEFORE INSERT OR UPDATE ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_md5()")

    cursor.execute("CREATE TRIGGER update_files_sha1 "
                   "BEFORE INSERT OR UPDATE ON files "
                   "FOR EACH ROW "
                   "EXECUTE PROCEDURE update_sha1()")
