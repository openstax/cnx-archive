# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import sys
import uuid
import base64

HASH_CHAR = '@'
VERSION_CHAR = '.'


__all__ = (
    'IdentHashSyntaxError',
    'IdentHashShortId',
    'IdentHashMissingVersion',
    'join_ident_hash',
    'split_ident_hash',
    'split_legacy_hash',
    'CNXHash',
    )


if sys.version_info >= (3,):
    basestring = (str, bytes)


class IdentHashError(Exception):
    """Base exception class for all ident hash exceptions."""
    def __str__(self):
        return self.msg


class IdentHashSyntaxError(IdentHashError):
    """Raised when the ident-hash syntax is incorrect."""
    def __init__(self, ident_hash):
        self.ident_hash = ident_hash
        self.msg = 'ident_hash={}'.format(ident_hash)


class IdentHashShortId(IdentHashError):
    """Raised when the ident-hash id is not a uuid"""
    def __init__(self, id, version):
        self.id = id
        self.version = version
        self.msg = 'id={} version={}'.format(id, version)


class IdentHashMissingVersion(IdentHashError):
    """Raised when the ident-hash does not have a version"""
    def __init__(self, id):
        self.id = id
        self.msg = 'id={}'.format(id)


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
    split_value = ident_hash.split(HASH_CHAR)

    if len(split_value) > 2 or '' in split_value:
        raise IdentHashSyntaxError(ident_hash)

    if len(split_value) == 1:
        id, version = split_value[0], ''
    else:
        id, version = split_value

    # Validate the id.
    id_type = CNXHash.validate(id)

    if id_type == CNXHash.SHORTID:
        raise IdentHashShortId(id, version)

    if not version:
        raise IdentHashMissingVersion(id)

    version = split_value[1]

    if split_version:
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


class CNXHash(uuid.UUID):
    SHORTID = 0
    BASE64HASH = 1
    FULLUUID = 2
    _SHORT_HASH_LENGTH = 8
    _MAX_SHORT_HASH_LENGTH = 22
    _HASH_PADDING_CHAR = b'='
    _HASH_DUMMY_CHAR = '0'

    def __init__(self, uu=None, *args, **kwargs):

        if isinstance(uu, uuid.UUID):
            uuid.UUID.__init__(self, bytes=uu.bytes)
        elif isinstance(uu, basestring):
            uuid.UUID.__init__(self, hex=uu)
        else:
            uuid.UUID.__init__(self, *args, **kwargs)

    def get_shortid(self):
        shortid = self.uuid2base64(self.__str__())[:self._SHORT_HASH_LENGTH]
        return shortid

    def get_base64id(self):
        """Return base64 encoded id."""
        base64id = self.uuid2base64(self.__str__())
        return base64id

    @classmethod
    def uuid2base64(cls, identifier):
        if isinstance(identifier, basestring):
            identifier = uuid.UUID(identifier)
        elif not(isinstance(identifier, uuid.UUID)):
            raise TypeError("must be uuid or string.")
        identifier = base64.urlsafe_b64encode(identifier.bytes)
        identifier = identifier.rstrip(cls._HASH_PADDING_CHAR)
        return identifier

    @classmethod
    def base642uuid(cls, identifier):
        if not(isinstance(identifier, basestring)):
            raise TypeError("must be a string.")
        try:
            identifier = str(identifier +
                             cls._HASH_PADDING_CHAR * (len(identifier) % 4))
            identifier = uuid.UUID(bytes=base64.urlsafe_b64decode(identifier))
        except TypeError:
            raise ValueError("badly formed string")
        return identifier

    @classmethod
    def validate(cls, hash_id):
        """Determine if ``hash_id`` is or could be a valid UUID."""
        if isinstance(hash_id, uuid.UUID) or isinstance(hash_id, cls):
            return cls.FULLUUID
        elif isinstance(hash_id, basestring):
            if len(hash_id) == cls._SHORT_HASH_LENGTH:
                try:  # convert short_id to one possible full hash to validate
                    hash_id = hash_id + \
                        cls._HASH_DUMMY_CHAR * \
                        (cls._MAX_SHORT_HASH_LENGTH -
                         cls._SHORT_HASH_LENGTH)
                    cls.base642uuid(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError(hash_id)
                return cls.SHORTID
            elif len(hash_id) == cls._MAX_SHORT_HASH_LENGTH:
                try:
                    cls.base642uuid(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError(hash_id)
                return cls.BASE64HASH
            else:  # See if it's a string repr of a uuid
                try:
                    cls.uuid2base64(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError(hash_id)
                return cls.FULLUUID
        raise IdentHashSyntaxError(hash_id)
