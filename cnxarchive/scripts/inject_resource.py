# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Commandline script used to inject a resource into the archive.
For example, to inject a book cover image into the archive.

Returns the path to the resource to stdout.

"""
from __future__ import print_function
import os
import sys
import hashlib
import subprocess

import psycopg2
from pyramid.paster import bootstrap

from cnxarchive.database import db_connect
from cnxarchive.scripts._utils import create_parser
from cnxarchive.utils import join_ident_hash, split_ident_hash


def guess_media_type(filepath):
    """Returns the media-type of the file at the given ``filepath``"""
    o = subprocess.check_output(['file', '--mime-type', '-Lb', filepath])
    o = o.strip()
    return o


def get_file_sha1(file):
    """Return the SHA1 hash of the given a file-like object as ``file``.
    This will seek the file back to 0 when it's finished.

    """
    bits = file.read()
    file.seek(0)
    h = hashlib.new('sha1', bits).hexdigest()
    return h


def lookup_module_ident(id, version):
    """Return the ``module_ident`` for the given ``id`` &
    major and minor version as a tuple.

    """
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT module_ident FROM modules "
                "WHERE uuid = %s "
                "AND CONCAT_WS('.', major_version, minor_version) = %s",
                (id, version))
            try:
                mident = cursor.fetchone()[0]
            except (IndexError, TypeError):
                ident_hash = join_ident_hash(id, version)
                raise RuntimeError("Content at {} does not exist."
                                   .format(ident_hash))
    return mident


def insert_file(file, media_type):
    """Upsert the ``file`` and ``media_type`` into the files table.
    Returns the ``fileid`` and ``sha1`` of the upserted file.

    """
    resource_hash = get_file_sha1(file)
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT fileid FROM files WHERE sha1 = %s",
                           (resource_hash,))
            try:
                fileid = cursor.fetchone()[0]
            except (IndexError, TypeError):
                cursor.execute("INSERT INTO files (file, media_type) "
                               "VALUES (%s, %s)"
                               "RETURNING fileid",
                               (psycopg2.Binary(file.read()), media_type,))
                fileid = cursor.fetchone()[0]
    return fileid, resource_hash


def upsert_module_file(module_ident, fileid, filename):
    """Upsert a file associated with ``fileid`` with ``filename``
    as a module_files entry associated with content at ``module_ident``.

    """
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT true FROM module_files "
                           "WHERE module_ident = %s "
                           "AND filename = %s",
                           (module_ident, filename,))
            try:
                cursor.fetchone()[0]
            except (IndexError, TypeError):
                cursor.execute("INSERT INTO module_files "
                               "(module_ident, fileid, filename) "
                               "VALUES (%s, %s, %s)",
                               (module_ident, fileid, filename,))
            else:
                cursor.execute("UPDATE module_files "
                               "SET (fileid) = (%s) "
                               "WHERE module_ident = %s AND filename = %s",
                               (fileid, module_ident, filename,))


def inject_resource(ident_hash, file, filename, media_type):
    """Injects the contents of ``file`` (a file-like object) into the database
    as ``filename`` with ``media_type`` in association with the content
    at ``ident_hash``.

    """
    resource_hash = get_file_sha1(file)
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            s_ident_hash = split_ident_hash(ident_hash)
            module_ident = lookup_module_ident(*s_ident_hash)
            fileid, resource_hash = insert_file(file, media_type)
            upsert_module_file(module_ident, fileid, filename)
    return resource_hash


def main(argv=None):
    parser = create_parser('inject_resource', description=__doc__)
    parser.add_argument('--media-type',
                        help="explicitly set the media-type")
    parser.add_argument('--resource-filename',
                        help="filename of the resource, overrides the input")
    parser.add_argument('ident_hash',
                        help="ident-hash of the content "
                             "to associate the resource with")
    parser.add_argument('resource',
                        help="filename to the resource")
    args = parser.parse_args(argv)

    env = bootstrap(args.config_uri)

    media_type = args.media_type
    ident_hash = args.ident_hash
    resource = args.resource
    filename = args.resource_filename

    # Discover the filename from the given resource.
    if filename is None:
        filename = os.path.basename(resource)

    # Guess the media-type from the given resource.
    if media_type is None:
        media_type = guess_media_type(resource)

    # Print some feedback incase of strange inputs
    print("Using:", file=sys.stderr)
    print("  filename: {}".format(filename), file=sys.stderr)
    print("  media_type: {}".format(media_type), file=sys.stderr)

    with open(resource, 'r') as file:
        rhash = inject_resource(ident_hash, file, filename, media_type)

    # Print the path to the resource.
    uri = env['request'].route_path('resource', hash=rhash)
    print(uri, file=sys.stdout)

    return 0


if __name__ == '__main__':  # pragma: no cover
    main()
