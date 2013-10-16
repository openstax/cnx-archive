# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import cgi
import os
import json
import logging
import psycopg2
from cnxquerygrammar.query_parser import grammar, DictFormater

from . import get_settings
from . import httpexceptions
from .utils import split_ident_hash, portaltype_to_mimetype, slugify
from .database import CONNECTION_SETTINGS_KEY, SQL
from .search import (
    search as database_search, Query,
    QUERY_TYPES, DEFAULT_QUERY_TYPE,
    )


logger = logging.getLogger('cnxarchive')


def get_content_metadata(id, version, cursor):
    """Return metadata related to the content from the database
    """
    # Do the module lookup
    args = dict(id=id, version=version)
    # FIXME We are doing two queries here that can hopefully be
    #       condensed into one.
    cursor.execute(SQL['get-module-metadata'], args)
    try:
        result = cursor.fetchone()[0]
        # version is what we want to return, but in the sql we're using
        # current_version because otherwise there's a "column reference is
        # ambiguous" error
        result['version'] = result.pop('current_version')

        return result
    except (TypeError, IndexError,):  # None returned
        raise httpexceptions.HTTPNotFound()

def get_content(environ, start_response):
    """Retrieve a piece of content using the ident-hash (uuid@version)."""
    settings = get_settings()
    ident_hash = environ['wsgiorg.routing_args']['ident_hash']
    id, version = split_ident_hash(ident_hash)

    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                cursor.execute(SQL['get-module-versions'], {'id': id})
                try:
                    latest_version = cursor.fetchone()[0]
                except (TypeError, IndexError,): # None returned
                    logger.debug("version was not supplied "
                                 "and could not be discovered.")
                    raise httpexceptions.HTTPNotFound()
                raise httpexceptions.HTTPFound('/contents/{}@{}' \
                        .format(id, latest_version,))
            result = get_content_metadata(id, version, cursor)
            # FIXME The 'mediaType' value will be changing to mimetypes
            #       in the near future.
            if result['mediaType'] == 'Collection':
                # Grab the collection tree.
                query = SQL['get-tree-by-uuid-n-version']
                args = dict(id=result['id'], version=result['version'])
                cursor.execute(query, args)
                tree = cursor.fetchone()[0]
                # Must unparse, otherwise we end up double encoding.
                result['tree'] = json.loads(tree)
            else:
                # Grab the html content.
                args = dict(id=id, filename='index.html')
                cursor.execute(SQL['get-resource-by-filename'], args)
                try:
                    content = cursor.fetchone()[0]
                except (TypeError, IndexError,):  # None returned
                    logger.debug("module found, but 'index.html' is missing.")
                    raise httpexceptions.HTTPNotFound()
                result['content'] = content[:]

    # FIXME We currently have legacy 'portal_type' names in the database.
    #       Future upgrades should replace the portal type with a mimetype
    #       of 'application/vnd.org.cnx.(module|collection|folder|<etc>)'.
    #       Until then we will do the replacement here.
    result['mediaType'] = portaltype_to_mimetype(result['mediaType'])

    result = json.dumps(result)
    status = "200 OK"
    headers = [('Content-type', 'application/json',)]
    start_response(status, headers)
    return [result]


def get_resource(environ, start_response):
    """Retrieve a file's data."""
    settings = get_settings()
    hash = environ['wsgiorg.routing_args']['hash']

    # Do the module lookup
    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            args = dict(hash=hash)
            cursor.execute(SQL['get-resource'], args)
            try:
                mimetype, file = cursor.fetchone()
            except TypeError:  # None returned
                raise httpexceptions.HTTPNotFound()

    status = "200 OK"
    headers = [('Content-type', mimetype)]
    start_response(status, headers)
    return [file[:]]


TYPE_INFO = {}
def get_type_info():
    if TYPE_INFO:
        return
    for line in get_settings()['exports-allowable-types'].splitlines():
        if not line.strip():
            continue
        type_name, type_info = line.strip().split(':', 1)
        type_info = type_info.split(',', 2)
        TYPE_INFO[type_name] = {
                'type_name': type_name,
                'file_extension': type_info[0],
                'mimetype': type_info[1],
                'user_friendly_name': type_info[2],
                }

def get_export_allowable_types(environ, start_response):
    """Return export types
    """
    get_type_info()
    headers = [('Content-type', 'application/json')]
    start_response('200 OK', headers)
    return [json.dumps(TYPE_INFO)]

def get_export(environ, start_response):
    """Retrieve an export file."""
    settings = get_settings()
    exports_dirs = settings['exports-directories'].split()
    args = environ['wsgiorg.routing_args']
    ident_hash, type = args['ident_hash'], args['type']
    id, version = split_ident_hash(ident_hash)
    get_type_info()

    if type not in TYPE_INFO:
        logger.debug("invalid type '{}' requested.".format(type))
        raise httpexceptions.HTTPNotFound()

    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                cursor.execute(SQL['get-module-versions'], {'id': id})
                try:
                    latest_version = cursor.fetchone()[0]
                except (TypeError, IndexError,): # None returned
                    logger.debug("version was not supplied "
                                 "and could not be discovered.")
                    raise httpexceptions.HTTPNotFound()
                raise httpexceptions.HTTPFound('/exports/{}@{}.{}' \
                        .format(id, latest_version, type))
            result = get_content_metadata(id, version, cursor)

    file_extension = TYPE_INFO[type]['file_extension']
    mimetype = TYPE_INFO[type]['mimetype']
    filename = '{}-{}.{}'.format(id, version, file_extension)

    status = "200 OK"
    headers = [('Content-type', mimetype,),
               ('Content-disposition',
                'attached; filename={}.{}'.format(slugify(result['title']),
                    file_extension),),
               ]

    for exports_dir in exports_dirs:
        try:
            with open(os.path.join(exports_dir, filename), 'r') as file:
                start_response(status, headers)
                return [file.read()]
        except IOError:
            # to be handled by the else part below if unable to find file in
            # any of the export dirs
            pass
    else:
        raise httpexceptions.HTTPNotFound()


MEDIA_TYPES = {
        'Collection': 'book',
        'Module': 'page',
        }


def search(environ, start_response):
    """Search API
    """
    empty_response = json.dumps({
        u'query': {
            u'limits': [],
            },
        u'results': {
            u'items': [],
            u'total': 0,
            u'limits': [{u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
            },
        })

    params = cgi.parse_qs(environ.get('QUERY_STRING', ''))
    try:
        search_terms = params.get('q', [])[0]
    except IndexError:
        start_response('200 OK', [('Content-type', 'application/json')])
        return [empty_response]
    query_type = params.get('t', None)
    if query_type is None or query_type not in QUERY_TYPES:
        query_type = DEFAULT_QUERY_TYPE

    query = Query.from_raw_query(search_terms)
    if not(query.filters or query.terms):
        start_response('200 OK', [('Content-type', 'application/json')])
        return [empty_response]
    db_results = database_search(query, query_type)

    results = {}
    limits = [{keyword: value} for keyword, value in query.terms]
    limits.extend([{keyword: value} for keyword, value in query.filters])
    results['query'] = {
            'limits': limits,
            'sort': query.sorts,
            }
    results['results'] = {'total': len(db_results), 'items': []}
    for record in db_results:
        results['results']['items'].append({
            'id': record['id'],
            'mediaType': record['mediaType'],
            'title': record['title'],
            'authors': record['authors'],
            'keywords': record['keywords'],
            'summarySnippet': record.highlighted_abstract,
            'bodySnippet': record.highlighted_fulltext,
            'pubDate': record['pubDate'],
            })
    result_limits = []
    for count_name, values in db_results.counts.items():
        for keyword, count in values.items():
            result_limits.append({count_name:keyword, 'count': count})
    results['results']['limits'] = result_limits

    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    return [json.dumps(results)]
