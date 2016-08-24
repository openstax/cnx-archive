# -*- coding: utf-8 -*-
import os
import sys


def up(cursor):
    """Install venv schema and session_preload if in a virtualenv."""

    if hasattr(sys, 'real_prefix'):
        activate_path = os.path.join(
            os.path.realpath(sys.prefix),
            'bin/activate_this.py')
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]

        cursor.execute("""SELECT schema_name FROM
                          information_schema.schemata
                          WHERE schema_name = 'venv';""")
        schema_exists = cursor.fetchall()

        if not schema_exists:
            cursor.execute("CREATE SCHEMA venv")
            cursor.execute("ALTER DATABASE \"{}\" SET "
                           "session_preload_libraries ="
                           "'session_exec'".format(db_name))
            cursor.execute("ALTER DATABASE \"{}\" SET "
                           "session_exec.login_name = "
                           "'venv.activate_venv'"
                           .format(db_name))
            sql = """CREATE FUNCTION venv.activate_venv()
RETURNS void LANGUAGE plpythonu AS $_$
import sys
import os
import site
old_os_path = os.environ.get('PATH','')
os.environ['PATH'] = os.path.dirname(os.path.abspath('{activate_path}')) \
+ os.pathsep + old_os_path
base = os.path.dirname(os.path.dirname(os.path.abspath('{activate_path}')))
site_packages = os.path.join(base, 'lib', 'python%s' % sys.version[:3], \
'site-packages')
prev_sys_path = list(sys.path)
site.addsitedir(site_packages)
sys.real_prefix = sys.prefix
sys.prefix = base
# Move the added items to the front of the path:
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path
$_$""".format(activate_path=activate_path)
            cursor.execute(sql)


def down(cursor):
    """Remove venvs schema and reset config."""
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]

    cursor.execute("ALTER DATABASE \"{}\" RESET "
                   "session_preload_libraries".format(db_name))
    cursor.execute("ALTER DATABASE \"{}\" RESET "
                   "session_exec.login_name".format(db_name))
    cursor.execute("DROP SCHEMA IF EXISTS venv CASCADE")
