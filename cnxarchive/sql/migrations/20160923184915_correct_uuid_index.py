# -*- coding: utf-8 -*-


def up(cursor):
    # Create correct index, drop less useful one
    cursor.execute("""
    CREATE INDEX modules_uuid_txt_version_idx ON modules
    (cast(uuid as text), module_version(major_version, minor_version));
    CREATE INDEX latest_modules_uuid_txt_version_idx ON latest_modules
    (cast(uuid as text), module_version(major_version, minor_version));
    DROP INDEX modules_uuid_version_idx;
    DROP INDEX latest_modules_uuid_version_idx;
    """)


def down(cursor):
    # Drop correct index, create less useful one
    cursor.execute("""
    CREATE INDEX modules_uuid_version_idx ON modules
    (uuid, module_version(major_version, minor_version));
    CREATE INDEX latest_modules_uuid_version_idx ON latest_modules
    (uuid, module_version(major_version, minor_version));
    DROP INDEX modules_uuid_txt_version_idx;
    DROP INDEX latest_modules_uuid_txt_version_idx;
    """)
