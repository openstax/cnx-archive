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
    'CNXHash',
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



class CNXHash(uuid.UUID):
    short_hash_length = 8
    max_short_hash_length = 22
    SHORTID = 0
    BASE64HASH = 1
    FULLUUID = 2
    HASH_PADDING_CHAR = '='

    def __init__(self, uu=None, *args, **kwargs):

        if isinstance(uu, uuid.UUID):
            uuid.UUID.__init__(self, bytes=uu.get_bytes())
        elif isinstance(uu, basestring):
            uuid.UUID.__init__(self, hex=uu)
        else:
            uuid.UUID.__init__(self, *args, **kwargs)

    def get_shortid(self):
        shortid = self.uuid2base64(self.__str__())[:self.short_hash_length]
        return shortid

    @classmethod
    def uuid2base64(cls,identifier):
        if isinstance(identifier, basestring):
            identifier = uuid.UUID(identifier)
        elif not(isinstance(identifier, uuid.UUID)):
            raise TypeError(" must be uuid or string.")
        identifier = base64.urlsafe_b64encode(identifier.get_bytes())
        identifier = identifier.rstrip(cls.HASH_PADDING_CHAR)
        return identifier

    @classmethod
    def base642uuid(cls,identifier):
        if not(isinstance(identifier, basestring)):
            raise TypeError(" must be a string.")
        try:
            identifier = str(identifier +
                             cls.HASH_PADDING_CHAR * (len(identifier) % 4))
            identifier = uuid.UUID(bytes=base64.urlsafe_b64decode(identifier))
        except TypeError:
            raise ValueError(" badly formed string")
        return identifier

    @classmethod
    def identifiers_similar(cls, identifier1, identifier2):
        shortid1=None
        shortid2=None

        try:
            type1=cls.validate(identifier1)
            type2=cls.validate(identifier2)
        except IdentHashSyntaxError:
            return False
        
        if isinstance(identifier1,cls):
            shortid1=identifier1.get_shortid()
        elif type1==cls.FULLUUID:
            shortid1=cls.uuid2base64(identifier1)[:cls.short_hash_length]
        elif type1==cls.BASE64HASH:
            shortid1=identifier1[cls.short_hash_length]
        elif type1==cls.SHORTID:
            shortid1=identifier1
        else:
            return False

        if isinstance(identifier2,cls):
            shortid2=identifier2.get_shortid()
        elif type2==cls.FULLUUID:
            shortid2=cls.uuid2base64(identifier2)[:cls.short_hash_length]
        elif type2==cls.BASE64HASH:
            shortid2=identifier2[cls.short_hash_length]
        elif type2==cls.SHORTID:
            shortid2=identifier2
        else:
            return False
                    
        return shortid1==shortid2 
           
    def equal(self,identifier):
        identifier1=self.__str__()
        identifier2=identifier
        return self.identifiers_equal(identifier1,identifier2)

    def similar(self,identifier):
        identifier1=self.__str__()
        identifier2=identifier
        return self.identifiers_similar(identifier1,identifier2)

    @classmethod
    def identifiers_equal(cls, identifier1, identifier2):
        fulluuid1=None
        fulluuid2=None
        shortid1=None
        shortid2=None

        try:
            type1=cls.validate(identifier1)
            type2=cls.validate(identifier2)
        except IdentHashSyntaxError:
            return False

        if type1==cls.FULLUUID:
            if (isinstance(fulluuid1,cls) or isinstance(fulluuid1,uuid.UUID)):
                fulluuid1=identifier1.__str__()
            else:
                fulluuid1=identifier1
        elif type1==cls.BASE64HASH:
            fulluuid1=cls.base642uuid(identifier1).__str__()
        elif type1==cls.SHORTID:
            shortid1=identifier1
        else:
            return False

        if type2==cls.FULLUUID:
            if (isinstance(fulluuid2,cls) or isinstance(fulluuid2,uuid.UUID)):
                fulluuid2=identifier2.__str__()
            else:
                fulluuid2=identifier2
        elif type2==cls.BASE64HASH:
            fulluuid2=cls.base642uuid(identifier2).__str__()
        elif type2==cls.SHORTID:
            shortid2=identifier2
        else:
            return False

        return (fulluuid1==fulluuid2) or (shortid1==shortid2)


    @classmethod
    def validate(cls, hash_id):
        if isinstance(hash_id, uuid.UUID):
            return cls.FULLUUID
        elif isinstance(hash_id, basestring):
            if len(hash_id) == cls.short_hash_length:
                try:  # convert short_id to one possible full hash to validate
                    hash_id = hash_id + '0'*(cls.max_short_hash_length -
                                             cls.short_hash_length)
                    cls.base642uuid(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError
                return cls.SHORTID
            elif len(hash_id) == cls.max_short_hash_length:
                try:
                    cls.base642uuid(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError
                return cls.BASE64HASH
            else:  # See if it's a string repr of a uuid
                try:
                    cls.uuid2base64(hash_id)
                except (TypeError, ValueError):
                    raise IdentHashSyntaxError
                return cls.FULLUUID
        raise IdentHashSyntaxError
