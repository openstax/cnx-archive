# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""select subcol_uuids(uuid, module_version(major_version, minor_version))
            FROM modules where portal_type = 'Collection';""")

    cursor.execute("""
    UPDATE modules SET stateid = 5
    WHERE
        portal_type = 'Collection' AND
        is_baked(uuid, module_version(major_version, minor_version))""")


def down(cursor):
    cursor.execute("""
    UPDATE trees
    SET documentid = NULL
    FROM modules m
    WHERE m.module_ident  = documentid AND portal_type = 'SubCollection';""")

    cursor.execute("""DELETE FROM modules WHERE portal_type = 'SubCollection';
    DELETE FROM document_acl da
    WHERE NOT EXISTS (SELECT 1 FROM modules m WHERE m.uuid = da.uuid);
    DELETE FROM document_controls dc
    WHERE NOT EXISTS (SELECT 1 FROM modules m WHERE m.uuid = dc.uuid);
    ;""")
