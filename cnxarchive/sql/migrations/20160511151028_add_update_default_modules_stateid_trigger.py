# -*- coding: utf-8 -*-
"""Add a trigger on modules to set all new inserted books to have state
"post-publication" in case there is a ruleset for collation.
"""


def up(cursor):
    cursor.execute("""\
CREATE OR REPLACE FUNCTION update_default_modules_stateid ()
RETURNS TRIGGER
LANGUAGE PLPGSQL
AS $$
BEGIN
  IF NEW.portal_type = 'Collection' THEN
    NEW.stateid = 5;
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER update_default_modules_stateid
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_default_modules_stateid();""")


def down(cursor):
    cursor.execute(
        'DROP TRIGGER IF EXISTS update_default_modules_stateid ON modules')
    cursor.execute('DROP FUNCTION IF EXISTS update_default_modules_stateid()')
