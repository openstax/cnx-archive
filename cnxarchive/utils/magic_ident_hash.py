# -*- coding: utf-8 -*-
from cnxcommon.ident_hash import *


__all__ = (
    'magically_split_ident_hash',
)


def _discover_bits(x):
    """Discover the missing bits of an ident-hash"""
    # Importing from views isn't great, but this code is destine to die,
    # so deal with it. =))
    from cnxarchive.views.helpers import get_uuid, get_latest_version
    try:
        uuid, version = split_ident_hash(x)
    except IdentHashShortId as exc:
        uuid = get_uuid(exc.id)
        version = exc.version
        uuid, version = _discover_bits(join_ident_hash(uuid, version))
    except IdentHashMissingVersion as e:
        uuid = e.id
        version = get_latest_version(e.id)
        uuid, version = _discover_bits(join_ident_hash(uuid, version))
    return uuid, version


def magically_split_ident_hash(x):
    """Magically split the ident_hash into a Book ident-hash and
    Page ident-hash. Both bits of information will be returned regardless
    of one missing. It should not be assumed that a returned Page ident-hash
    actually refers to a piece of content that is a Page.

    """
    if ':' in x:
        book_ih, page_ih = x.split(':')
        book_ih = _discover_bits(book_ih)
        page_ih = _discover_bits(page_ih)
    else:
        book_ih = None
        page_ih = _discover_bits(x)
    return book_ih, page_ih
