# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""All the views."""
import os
import json
import logging
from datetime import datetime, timedelta
from re import compile

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from .. import cache
# FIXME double import
from .. import database
from ..database import SQL, get_tree, get_collated_content
from ..search import (
    DEFAULT_PER_PAGE, QUERY_TYPES, DEFAULT_QUERY_TYPE,
    Query,
    )
from ..sitemap import Sitemap
from ..robots import Robots
from ..utils import (
    COLLECTION_MIMETYPE, IdentHashSyntaxError,
    IdentHashShortId, IdentHashMissingVersion,
    portaltype_to_mimetype, slugify, fromtimestamp,
    join_ident_hash, split_ident_hash, split_legacy_hash
    )
from .content import _get_content_json

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']

logger = logging.getLogger('cnxarchive')

# #################### #
#   Helper functions   #
# #################### #


# ######### #
#   Views   #
# ######### #


@view_config(route_name='resource', request_method='GET')
def get_resource(request):
    """Retrieve a file's data."""
    settings = get_current_registry().settings
    hash = request.matchdict['hash']

    # Do the file lookup
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            args = dict(hash=hash)
            cursor.execute(SQL['get-resource'], args)
            try:
                mimetype, file = cursor.fetchone()
            except TypeError:  # None returned
                raise httpexceptions.HTTPNotFound()

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = mimetype
    resp.body = file[:]
    return resp
