# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Exception Views."""
import logging

from pyramid import httpexceptions
from pyramid.view import view_config

from ..utils import (
    IdentHashSyntaxError, IdentHashShortId, IdentHashMissingVersion,
    join_ident_hash, split_ident_hash
    )
from .helpers import get_latest_version
from .helpers import get_uuid

logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


# ################### #
#   Exception Views   #
# ################### #


@view_config(context=IdentHashSyntaxError)
def ident_hash_syntax_error(exc, request):
    if exc.ident_hash.endswith('@'):
        try:
            split_ident_hash(exc.ident_hash[:-1])
        except IdentHashShortId as e:
            return ident_hash_short_id(e, request)
        except IdentHashMissingVersion as e:
            return ident_hash_missing_version(e, request)
        except IdentHashSyntaxError:
            pass
    return httpexceptions.HTTPNotFound()


@view_config(context=IdentHashShortId)
def ident_hash_short_id(exc, request):
    try:
        uuid_ = get_uuid(exc.id)
    except httpexceptions.HTTPNotFound as e:
        return e
    if not exc.version:
        return ident_hash_missing_version(
            IdentHashMissingVersion(uuid_, exc.containing), request)
    route_name = request.matched_route.name
    route_args = request.matchdict.copy()
    route_args['ident_hash'] = join_ident_hash(uuid_, exc.version)
    return httpexceptions.HTTPMovedPermanently(request.route_path(
        route_name, _query=request.params, **route_args),
        headers=[("Cache-Control", "max-age=31536000, public")])


@view_config(context=IdentHashMissingVersion)
def ident_hash_missing_version(exc, request):
    try:
        version = get_latest_version(exc.id, exc.containing)
    except httpexceptions.HTTPNotFound as e:
        return e
    route_name = request.matched_route.name
    route_args = request.matchdict.copy()
    route_args['ident_hash'] = join_ident_hash(exc.id, version)
    return httpexceptions.HTTPFound(request.route_path(
        route_name, _query=request.params, **route_args),
        headers=[("Cache-Control", "max-age=60, public")])
