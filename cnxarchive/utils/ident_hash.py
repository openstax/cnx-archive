# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import uuid
import tzlocal


HASH_CHAR = '@'
VERSION_CHAR = '.'


__all__ = (
    'IdentHashSyntaxError',
    'join_ident_hash',
    'split_ident_hash',
    'split_legacy_hash',
    )


class IdentHashSyntaxError(Exception):
    """Raised when the ident-hash syntax is incorrect."""


def split_legacy_hash(legacy_hash):
    split_value = legacy_hash.split('/')
    id = split_value[0]
    version = None
    if len(split_value) == 2:
        if split_value[1] != 'latest':
            version = split_value[1]
    return id, version


def split_ident_hash(ident_hash, split_version=False):
    """Returns a valid id and version from the <id>@<version> hash syntax."""
    if HASH_CHAR not in ident_hash:
        ident_hash = '{}@'.format(ident_hash)
    split_value = ident_hash.split(HASH_CHAR)
    if split_value[0] == '':
        raise ValueError("Missing values")

    try:
        id, version = split_value
    except ValueError:
        raise IdentHashSyntaxError(ident_hash)

    # Validate the id.
    try:
        uuid.UUID(id)
    except ValueError:
        raise IdentHashSyntaxError(
            "invalid identification value, {}".format(id))
    # None'ify the version on empty string.
    version = version and version or None

    if split_version:
        if version is None:
            version = (None, None,)
        else:
            split_version = version.split(VERSION_CHAR)
            if len(split_version) == 1:
                split_version.append(None)
            version = tuple(split_version)
    return id, version


def join_ident_hash(id, version):
    """Returns a valid ident_hash from the given ``id`` and ``version``
    where ``id`` can be a string or UUID instance and ``version`` can be a
    string or tuple of major and minor version.
    """
    if isinstance(id, uuid.UUID):
        id = str(id)
    join_args = [id]
    if isinstance(version, (tuple, list,)):
        assert len(version) == 2, "version sequence must be two values."
        version = VERSION_CHAR.join([str(x) for x in version if x is not None])
    if version:
        join_args.append(version)
    return HASH_CHAR.join(join_args)
