# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
ALTER TABLE modules
  ALTER COLUMN stateid SET DEFAULT 1""")


def down(cursor):
    cursor.execute("""\
ALTER TABLE modules
  ALTER COLUMN stateid DROP DEFAULT""")
