# -*- coding: utf-8 -*-
"""\
- Add SQL function `pypath`
- Add SQL function `pyimport`

"""

def up(cursor):
    # Add SQL function `pypath`
    cursor.execute("""\
-- Returns the Python `sys.path`
--   Example usage, `SELECT unnest(pypath())`
CREATE OR REPLACE FUNCTION pypath()
  RETURNS TEXT[]
  AS $$
import sys
return sys.path
$$ LANGUAGE plpythonu;
    """)

    # Add SQL function `pyimport`
    cursor.execute("""\
-- Returns module location for the given module
--   Example usage, `SELECT * FROM pyimport('cnxarchive.database');`
CREATE TYPE pyimport_value AS (
  import TEXT,
  directory TEXT,
  file_path TEXT
);
CREATE OR REPLACE FUNCTION pyimport(pymodule TEXT)
  RETURNS SETOF pyimport_value
  AS $$
import os
import importlib
try:
    module = importlib.import_module(pymodule)
except ImportError:
    return []  #{'import': None, 'directory': None, 'file_path': None}
file_path = os.path.abspath(module.__file__)
directory = os.path.dirname(file_path)
info = {
    'import': pymodule,
    'directory': directory,
    'file_path': file_path,
}
return [info]
$$ LANGUAGE plpythonu;
    """)


def down(cursor):
    # Remove SQL function `pypath`
    cursor.execute("DROP FUNCTION IF EXISTS pypath();")

    # Remove SQL function `pyimport`
    cursor.execute("DROP TYPE IF EXISTS pyimport_value CASCADE;")
