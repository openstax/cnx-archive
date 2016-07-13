# -*- coding: utf-8 -*-
"""\
Add more states to modulestates for post publication
"""


def up(cursor):
    cursor.execute("""\
        INSERT INTO modulestates (stateid, statename) VALUES
            (5, 'post-publication'),
            (6, 'processing'),
            (7, 'errored')""")


def down(cursor):
    cursor.execute("""\
        DELETE FROM modulestates WHERE statename IN
            ('post-publication', 'processing', 'errored')""")
    cursor.execute("""\
        SELECT setval('modulestates_stateid_seq', 5, false)""")
