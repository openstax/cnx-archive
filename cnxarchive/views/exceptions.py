# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Exception Views."""
import os
import json
import logging
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from . import config
from .database import SQL, get_tree, get_collated_content
from .utils import (
    COLLECTION_MIMETYPE, IdentHashSyntaxError,
    IdentHashShortId, IdentHashMissingVersion,
    portaltype_to_mimetype, slugify, fromtimestamp,
    join_ident_hash, split_ident_hash, split_legacy_hash
    )

logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


def get_uuid(shortid):
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-module-uuid'], {'id': shortid})
            try:
                return cursor.fetchone()[0]
            except (TypeError, IndexError,):  # None returned
                logger.debug("Short ID was supplied and could not discover "
                             "UUID.")
                raise httpexceptions.HTTPNotFound()


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
            IdentHashMissingVersion(uuid_), request)
    route_name = request.matched_route.name
    route_args = request.matchdict.copy()
    route_args['ident_hash'] = join_ident_hash(uuid_, exc.version)
    return httpexceptions.HTTPFound(request.route_path(
        route_name, _query=request.params, **route_args))


@view_config(context=IdentHashMissingVersion)
def ident_hash_missing_version(exc, request):
    try:
        version = get_latest_version(exc.id)
    except httpexceptions.HTTPNotFound as e:
        return e
    route_name = request.matched_route.name
    route_args = request.matchdict.copy()
    route_args['ident_hash'] = join_ident_hash(exc.id, version)
    return httpexceptions.HTTPFound(request.route_path(
        route_name, _query=request.params, **route_args))
