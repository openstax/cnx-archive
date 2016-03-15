# -*- coding: utf-8 -*-
"""\
- Remove `re_safe_word` column from the database, if it exists.
- Remove keywords that only contain XML.
- Strip XML from keywords, if they contain XML

"""


def up(cursor):
    # Remove `re_safe_word` column from the database, if it exists.
    cursor.execute("ALTER TABLE keywords DROP COLUMN IF EXISTS re_safe_word")
    # Remove keywords that only contain XML.
    cursor.execute("""\
    WITH kwids AS (
      DELETE FROM keywords
      WHERE word ~ '<' AND regexp_replace(word, '<.*?>', '', 'g') != ''
      RETURNING keywordid
    )
    DELETE FROM modulekeywords
    WHERE keywordid = any(SELECT keywordid FROM kwids)
    """)
    # Strip XML from keywords, if they contain XML
    cursor.execute("""\
    UPDATE keywords SET word = regexp_replace(word, '<.*?>', '', 'g')
    WHERE word ~ '<'
    """)


def down(cursor):
    pass
