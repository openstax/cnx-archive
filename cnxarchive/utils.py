# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import uuid


class IdentHashSyntaxError(Exception):
    """Raised when the ident-hash syntax is incorrect."""


def split_ident_hash(ident_hash):
    """Returns a valid id and version from the <id>@<version> hash syntax."""
    split_value = ident_hash.split('@')
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
        raise IdentHashSyntaxError("invalid identification value, {}" \
                                       .format(id))
    # None'ify the version on empty string.
    version = version and version or None
    return id, version
