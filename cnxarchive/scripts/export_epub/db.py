# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Logic used to acquire data from the archive database.

"""
import os

from cnxarchive.database import db_connect
from cnxarchive.utils import (
    join_ident_hash,
    split_ident_hash,
    IdentHashMissingVersion,
    )

from cnxarchive.scripts.export_epub.exceptions import (
    NotFound,
    FileNotFound,
    ContentNotFound,
    )


here = os.path.abspath(os.path.dirname(__file__))
SQL_DIR = os.path.join(here, 'sql')


def _get_sql(filename):
    """Returns the contents of the sql file from the given ``filename``."""
    with open(os.path.join(SQL_DIR, filename), 'r') as f:
        return f.read()


def verify_id_n_version(id, version):
    """Given an ``id`` and ``version``, verify the identified content exists.

    """
    stmt = _get_sql('verify-id-and-version.sql')
    args = dict(id=id, version=version)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                valid = cursor.fetchone()[0]
            except TypeError:
                raise NotFound(join_ident_hash(id, version))
    return True


def get_id_n_version(ident_hash):
    """From the given ``ident_hash`` return the id and version."""
    try:
        id, version = split_ident_hash(ident_hash)
    except IdentHashMissingVersion:
        # XXX Don't import from views... And don't use httpexceptions
        from pyramid.httpexceptions import HTTPNotFound
        from cnxarchive.views.helpers import get_latest_version
        try:
            version = get_latest_version(ident_hash)
        except HTTPNotFound:
            raise NotFound(ident_hash)
        id, version = split_ident_hash(join_ident_hash(ident_hash, version))
    else:
        verify_id_n_version(id, version)

    return id, version


def get_type(ident_hash):
    """Return the database type for the given ``ident_hash``
    As of now, this could either be a 'Module' or 'Collection'.

    """
    id, version = get_id_n_version(ident_hash)

    stmt = _get_sql('get-type.sql')
    args = dict(id=id, version=version)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            type = cursor.fetchone()[0]
    return type


def get_metadata(ident_hash):
    """Return the dictionary of metadata from the database.
    This data is keyed using the cnx-epub data structure.

    """
    id, version = get_id_n_version(ident_hash)

    stmt = _get_sql('get-metadata.sql')
    args = dict(id=id, version=version)

    # FIXME The license_url and license_text metadata attributes need to
    # change to a License structure similar to what is used in cnx-authoring.

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                metadata = cursor.fetchone()[0]
            except TypeError:
                raise NotFound(ident_hash)
    return metadata


def get_content(ident_hash, context=None):
    """Returns the content for the given ``ident_hash``.
    ``context`` is optionally ident-hash used to find the content
    within the context of a Collection ident_hash.

    """
    id, version = get_id_n_version(ident_hash)
    filename = 'index.cnxml.html'

    if context is not None:
        stmt = _get_sql('get-baked-content.sql')
        args = dict(id=id, version=version, context=context)
    else:
        stmt = _get_sql('get-content.sql')
        args = dict(id=id, version=version, filename=filename)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                content, _ = cursor.fetchone()
            except TypeError:
                raise ContentNotFound(ident_hash, context, filename)
    return content[:]


def get_file_info(hash, context=None):
    """Returns information about the file, identified by ``hash``.
    If the `context` (an ident-hash) is supplied,
    the information returned will be specific to that context.

    """
    if context is None:
        stmt = _get_sql('get-file-info.sql')
        args = dict(hash=hash)
    else:
        stmt = _get_sql('get-file-info-in-context.sql')
        id, version = get_id_n_version(context)
        args = dict(hash=hash, id=id, version=version)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                filename, media_type = cursor.fetchone()
            except TypeError:
                raise FileNotFound(hash)
    return filename, media_type


def get_file(hash):
    """Return the contents of the file as a ``memoryview``."""
    stmt = _get_sql('get-file.sql')
    args = dict(hash=hash)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                file, _ = cursor.fetchone()
            except TypeError:
                raise FileNotFound(hash)
    return memoryview(file[:])


def get_registered_files(ident_hash):
    """Returns a list SHA1 hashes for registered file entries
    identified by the given module ``ident_hash``.

    Note, it's possible for a module to reference a file without having
    a registered file entry for it.

    Note, all files are included, including the raw form of the content.

    """
    id, version = get_id_n_version(ident_hash)

    stmt = _get_sql('get-registered-files-info.sql')
    args = dict(id=id, version=version)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            rows = cursor.fetchall()
    if rows is None:
        rows = []
    hashes = list(set([sha1 for sha1, _, __ in rows]))
    return hashes


def get_tree(ident_hash, baked=False):
    """Return a tree structure of the Collection"""
    id, version = get_id_n_version(ident_hash)

    stmt = _get_sql('get-tree.sql')
    args = dict(id=id, version=version, baked=baked)

    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(stmt, args)
            try:
                tree = cursor.fetchone()[0]
            except TypeError:
                raise NotFound(ident_hash)
    if tree is None:
        raise NotFound(ident_hash)

    return tree


__all__ = (
    'get_content',
    'get_file',
    'get_file_info',
    'get_id_n_version',
    'get_metadata',
    'get_registered_files',
    'get_tree',
    'get_type',
    )
