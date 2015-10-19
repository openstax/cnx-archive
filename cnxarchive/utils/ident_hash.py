# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import uuid
import tzlocal
import base64

HASH_CHAR = '@'
VERSION_CHAR = '.'


__all__ = (
    'IdentHashSyntaxError',
    'join_ident_hash',
    'split_ident_hash',
    'split_legacy_hash',
    "CNXHash"
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

    id_type = CNXHash.validate(id)

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
    return id, version, id_type


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

HASH_PADDING_CHAR = '='


class CNXHash(uuid.UUID):
    short_hash_length = 8
    max_short_hash_length = 22
    SHORTID = 0
    BASE64HASH = 1
    FULLUUID = 2

    def __init__(self, uu=None, *args, **kwargs):
        if type(uu) == uuid.UUID:
            uuid.UUID.__init__(self, bytes=uu.get_bytes())
        elif type(uu) == str:
            uuid.UUID.__init__(self, hex=uu)
        else:
            uuid.UUID.__init__(self, *args, **kwargs)

    def get_shortid(self):
        shortid = self.uuid2base64(self.__str__())[:self.short_hash_length]
        return shortid

    @staticmethod
    def uuid2base64(identifier):
        if type(identifier) == str:
            identifier = uuid.UUID(identifier)
        elif type(identifier) != uuid.UUID:
            raise TypeError(" must be uuid or string.")
        identifier = base64.urlsafe_b64encode(identifier.get_bytes())
        identifier = identifier.rstrip(HASH_PADDING_CHAR)
        return identifier

    @staticmethod
    def base642uuid(identifier):
        if type(identifier) != str:
            raise TypeError(" must be a string.")
        try:
            identifier = identifier+HASH_PADDING_CHAR*(len(identifier) % 4)
            identifier = uuid.UUID(bytes=base64.urlsafe_b64decode(identifier))
        except TypeError:
            raise ValueError(" badly formed string")
        return identifier

    @staticmethod
    def identifiers_equal(identifier1, identifier2):
        identifier1 = str(identifier1)
        identifier2 = str(identifier2)

        if len(identifier1) < len(identifier2):
            return identifier1 == uuid2base64(identifier2)
        if len(identifier1) == len(identifier2):
            return identifier1 == identifier2
        if len(identifier1) > len(identifier2):
            return uuid2base64(identifier1) == identifier2

    @classmethod
    def identifiers_similar(cls, identifier1, identifier2):
        identifier1 = str(identifier1)
        identifier2 = str(identifier2)

    @classmethod
    def validate(cls, hash_id):
        if type(hash_id) == cls or type(hash_id) == uuid.UUID:
            return cls.FULLUUID
        elif type(hash_id) == str and len(hash_id) == cls.short_hash_length:
            try:
                hash_id = hash_id + '0'*(cls.max_short_hash_length -
                                         cls.short_hash_length)
                cls.base642uuid(hash_id)
            except (TypeError, ValueError):
                raise IdentHashSyntaxError
            return cls.SHORTID
        elif type(hash_id) == str and \
                len(hash_id) == cls.max_short_hash_length:
            try:
                cls.base642uuid(hash_id)
            except (TypeError, ValueError):
                raise IdentHashSyntaxError
            return cls.BASE64HASH
        elif type(hash_id) == str \
                and len(hash_id) != cls.short_hash_length \
                and len(hash_id) != cls.max_short_hash_length:
            try:
                cls.uuid2base64(hash_id)
            except (TypeError, ValueError):
                raise IdentHashSyntaxError
            return cls.FULLUUID
        raise IdentHashSyntaxError
