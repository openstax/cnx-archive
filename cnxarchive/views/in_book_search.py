# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""In Book Search Views."""
import json
import logging

from pyramid.view import view_config

from ..database import SQL, db_connect
from ..utils import (
    IdentHashShortId, IdentHashMissingVersion, split_ident_hash
    )
from .helpers import get_uuid

logger = logging.getLogger('cnxarchive')

# #################### #
#   Helper functions   #
# #################### #


# ######### #
#   Views   #
# ######### #


@view_config(route_name='in-book-search', request_method='GET',
             http_cache=(31536000, {'public': True}))
def in_book_search(request):
    """Full text, in-book search."""
    results = {}

    args = request.matchdict
    ident_hash = args['ident_hash']

    args['search_term'] = request.params.get('q', '')
    query_type = request.params.get('query_type', '')
    combiner = ''
    if query_type:
        if query_type.lower() == 'or':
            combiner = '_or'

    id, version = split_ident_hash(ident_hash)
    args['uuid'] = id
    args['version'] = version

    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-collated-state'], args)
            res = cursor.fetchall()
            if res and res[0][0]:
                statement = SQL['get-in-collated-book-search']
            else:
                statement = SQL['get-in-book-search']
            cursor.execute(statement.format(combiner=combiner), args)
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


@view_config(route_name='in-book-search-page', request_method='GET',
             http_cache=(31536000, {'public': True}))
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

    query_type = request.params.get('query_type', '')
    combiner = ''
    if query_type:
        if query_type.lower() == 'or':
            combiner = '_or'

    # Get version from URL params
    id, version = split_ident_hash(ident_hash)
    args['uuid'] = id
    args['version'] = version

    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-collated-state'], args)
            res = cursor.fetchall()
            if res and res[0][0]:
                statement = SQL['get-in-collated-book-search-full-page']
            else:
                statement = SQL['get-in-book-search-full-page']
            cursor.execute(statement.format(combiner=combiner), args)
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
