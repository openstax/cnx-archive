# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
CREATE EXTENSION pg_trgm;
CREATE INDEX modules_strip_html_name_trgm_gin ON modules \
    USING gin(strip_html(name) gin_trgm_ops);
""")


def down(cursor):
    cursor.execute("""\
DROP INDEX IF EXISTS modules_strip_html_name_trgm_gin;
DROP EXTENSION IF EXISTS pg_trgm;
""")
