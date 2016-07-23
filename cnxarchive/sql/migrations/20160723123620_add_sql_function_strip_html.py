# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
CREATE OR REPLACE FUNCTION strip_html(html_text TEXT)
  RETURNS text
AS $$
  import re
  return re.sub('<[^>]*?>', '', html_text, re.MULTILINE)
$$ LANGUAGE plpythonu IMMUTABLE;
    """)


def down(cursor):
    cursor.execute("DROP FUNCTION IF EXISTS strip_html(TEXT)")
