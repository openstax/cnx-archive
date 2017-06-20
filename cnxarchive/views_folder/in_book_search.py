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

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']

logger = logging.getLogger('cnxarchive')

# #################### #
#   Helper functions   #
# #################### #

def _get_page_in_book(page_uuid, page_version, book_uuid,
                      book_version, latest=False):
    book_ident_hash = join_ident_hash(book_uuid, book_version)
    coltree = _get_content_json(ident_hash=book_ident_hash)['tree']
    if coltree is None:
        raise httpexceptions.HTTPNotFound()
    pages = list(flatten_tree_to_ident_hashes(coltree))
    page_ident_hash = join_ident_hash(page_uuid, page_version)
    if page_ident_hash in pages:
        return book_uuid, '{}:{}'.format(
            latest and book_uuid or book_ident_hash, page_uuid)
    # book not in page
    return page_uuid, page_ident_hash


# ######### #
#   Views   #
# ######### #


@view_config(route_name='in-book-search', request_method='GET')
def in_book_search(request):
    """Full text, in-book search."""
    results = {}

    args = request.matchdict
    ident_hash = args['ident_hash']

    args['search_term'] = request.params.get('q', '')

    id, version = split_ident_hash(ident_hash)
    args['uuid'] = id
    args['version'] = version

    settings = get_current_registry().settings
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-collated-state'], args)
            res = cursor.fetchall()
            if res and res[0][0]:
                statement = SQL['get-in-collated-book-search']
            else:
                statement = SQL['get-in-book-search']
            cursor.execute(statement, args)
            res = cursor.fetchall()

            results['results'] = {'query': [],
                                  'total': len(res),
                                  'items': []}
            results['results']['query'] = {
                'id': ident_hash,
                'search_term': args['search_term'],
            }
            for uuid, version, title, snippet, matches, rank in res:
                results['results']['items'].append({
                    'rank': '{}'.format(rank),
                    'id': '{}@{}'.format(uuid, version),
                    'title': '{}'.format(title),
                    'snippet': '{}'.format(snippet),
                    'matches': '{}'.format(matches),
                })

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    resp.body = json.dumps(results)

    return resp


@view_config(route_name='in-book-search-page', request_method='GET')
def in_book_search_highlighted_results(request):
    """In-book search - returns a highlighted version of the HTML."""
    results = {}

    args = request.matchdict
    ident_hash = args['ident_hash']

    page_ident_hash = args['page_ident_hash']
    try:
        page_uuid, _ = split_ident_hash(page_ident_hash)
    except IdentHashShortId as e:
        page_uuid = get_uuid(e.id)
    except IdentHashMissingVersion as e:
        page_uuid = e.id
    args['page_uuid'] = page_uuid

    args['search_term'] = request.params.get('q', '')

    # Get version from URL params
    id, version = split_ident_hash(ident_hash)
    args['uuid'] = id
    args['version'] = version

    settings = get_current_registry().settings
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-collated-state'], args)
            res = cursor.fetchall()
            if res and res[0][0]:
                statement = SQL['get-in-collated-book-search-full-page']
            else:
                statement = SQL['get-in-book-search-full-page']
            cursor.execute(statement, args)
            res = cursor.fetchall()

            results['results'] = {'query': [],
                                  'total': len(res),
                                  'items': []}
            results['results']['query'] = {
                'search_term': args['search_term'],
                'collection_id': ident_hash,
            }
            for uuid, version, title, headline, rank in res:
                results['results']['items'].append({
                    'rank': '{}'.format(rank),
                    'id': '{}'.format(page_ident_hash),
                    'title': '{}'.format(title),
                    'html': '{}'.format(headline),
                })

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    resp.body = json.dumps(results)

    return resp
