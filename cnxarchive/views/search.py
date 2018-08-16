# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Search Views."""
import json
import logging

from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

from .. import config
from .. import cache
from ..database import SQL, db_connect
from ..search import (
    DEFAULT_PER_PAGE, QUERY_TYPES, DEFAULT_QUERY_TYPE,
    Query,
    )

logger = logging.getLogger('cnxarchive')
_BLOCK_SIZE = 4096 * 64  # 256K

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']


# ######### #
#   Views   #
# ######### #


@view_config(route_name='search', request_method='GET',
             http_cache=(60, {'public': True}))
def search(request):
    """Search API."""
    empty_response = json.dumps({
        u'query': {
            u'limits': [],
            u'per_page': DEFAULT_PER_PAGE,
            u'page': 1,
            },
        u'results': {
            u'items': [],
            u'total': 0,
            u'limits': [],
            },
        })

    params = request.params
    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    search_terms = params.get('q', '')
    query_type = params.get('t', None)
    if query_type is None or query_type not in QUERY_TYPES:
        query_type = DEFAULT_QUERY_TYPE

    try:
        per_page = int(params.get('per_page', ''))
    except (TypeError, ValueError, IndexError):
        per_page = None
    if per_page is None or per_page <= 0:
        per_page = DEFAULT_PER_PAGE
    try:
        page = int(params.get('page', ''))
    except (TypeError, ValueError, IndexError):
        page = None
    if page is None or page <= 0:
        page = 1

    query = Query.from_raw_query(search_terms)
    if not(query.filters or query.terms):
        resp.body = empty_response
        return resp

    db_results = cache.search(
        query, query_type,
        nocache=params.get('nocache', '').lower() == 'true')

    authors = db_results.auxiliary['authors']
    # create a mapping for author id to index in auxiliary authors list
    author_mapping = {}
    for i, author in enumerate(authors):
        author_mapping[author['id']] = i

    results = {}
    limits = []
    for k, v in query.terms + query.filters:
        limits.append({'tag': k, 'value': v})
        if v in author_mapping:
            limits[-1]['index'] = author_mapping[v]
    results['query'] = {
        'limits': limits,
        'sort': query.sorts,
        'per_page': per_page,
        'page': page,
        }
    results['results'] = {'total': len(db_results), 'items': []}

    for record in db_results[((page - 1) * per_page):(page * per_page)]:
        results['results']['items'].append({
            'id': '{}@{}'.format(record['id'], record['version']),
            'mediaType': record['mediaType'],
            'title': record['title'],
            # provide the index in the auxiliary authors list
            'authors': [{
                'index': author_mapping[a['id']],
                'id': a['id'],
                } for a in record['authors']],
            'keywords': record['keywords'],
            'summarySnippet': record['abstract'],
            'bodySnippet': record['headline'],
            'pubDate': record['pubDate'],
            'weight': record['weight'],
            })
    result_limits = []
    for count_name, values in db_results.counts.items():
        if not values:
            continue
        result_limits.append({'tag': count_name,
                              'values': []})
        for keyword, count in values:
            value = {'value': keyword, 'count': count}
            # if it's an author, provide the index in auxiliary
            # authors list as well
            if keyword in author_mapping:
                value['index'] = author_mapping[keyword]
            result_limits[-1]['values'].append(value)
    results['results']['limits'] = result_limits
    # Add the supplemental result information.
    results['results']['auxiliary'] = db_results.auxiliary

    # In the case where a search is performed with an authorId
    # has a filter, it is possible for the database to return
    # no results even if the author exists in the database.
    #  Therefore, the database is queried a second time for
    # contact information associated with only the authorIds.
    #  The author information is then used to update the
    # results returned by the first database query.
    if len(db_results) <= 0:
        authors_results = []
        limits = results['query']['limits']
        index = 0
        statement = SQL['get-users-by-ids']
        with db_connect() as db_connection:
            with db_connection.cursor() as cursor:
                for idx, limit in enumerate(limits):
                    if limit['tag'] == 'authorID':
                        author = limit['value']
                        arguments = (author,)
                        cursor.execute(statement, arguments)
                        author_db_result = cursor.fetchall()
                        if author_db_result:
                            author_db_result = author_db_result[0][0]
                        else:
                            author_db_result = {'id': author, 'fullname': None}
                        authors_results.append(author_db_result)
                        limit['index'] = index
                        index = index + 1
                        limits[idx] = limit
        results['query']['limits'] = limits
        results['results']['auxiliary']['authors'] = authors_results

    resp.body = json.dumps(results)

    return resp
