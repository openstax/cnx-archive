# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
CREATE OR REPLACE FUNCTION post_publication() RETURNS trigger AS $$
BEGIN
  NOTIFY post_publication;
  RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER post_publication_trigger
  AFTER INSERT OR UPDATE ON modules FOR EACH ROW
  WHEN (NEW.stateid = 5)
  EXECUTE PROCEDURE post_publication();""")


def down(cursor):
    cursor.execute("""\
DROP TRIGGER post_publication_trigger ON modules;
DROP FUNCTION post_publication();""")
