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
import psycopg2
from cnxquerygrammar.query_parser import grammar, DictFormater

from . import get_settings
from . import httpexceptions
from .utils import split_ident_hash, portaltype_to_mimetype
from .database import CONNECTION_SETTINGS_KEY, SQL, DBQuery


def get_content(environ, start_response):
    """Retrieve a piece of content using the ident-hash (uuid@version)."""
    settings = get_settings()
    ident_hash = environ['wsgiorg.routing_args']['ident_hash']
    id, version = split_ident_hash(ident_hash)

    # Do the module lookup
    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            args = dict(id=id, version=version)
            # FIXME We are doing two queries here that can hopefully be
            #       condensed into one.
            cursor.execute(SQL['get-module-metadata'], args)
            try:
                result = cursor.fetchone()[0]
            except (TypeError, IndexError,):  # None returned
                raise httpexceptions.HTTPNotFound()
            # FIXME The 'mediaType' value will be changing to mimetypes
            #       in the near future.
            if result['mediaType'] == 'Collection':
                # Grab the collection tree.
                result['tree'] = None  # TODO
            else:
                # Grab the html content.
                args = dict(id=id, filename='index.html')
                cursor.execute(SQL['get-resource-by-filename'], args)
                try:
                    content = cursor.fetchone()[0]
                except (TypeError, IndexError,):  # None returned
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
    id = environ['wsgiorg.routing_args']['id']

    # Do the module lookup
    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            args = dict(id=id)
            cursor.execute(SQL['get-resource'], args)
            try:
                filename, mimetype, file = cursor.fetchone()
            except TypeError:  # None returned
                raise httpexceptions.HTTPNotFound()

    status = "200 OK"
    headers = [('Content-type', mimetype,),
               ('Content-disposition',
                "attached; filename={}".format(filename),),
               ]
    start_response(status, headers)
    return [file]


TYPE_INFO = {
    # <type-name>: (<file-extension>, <mimetype>,),
    'pdf': ('pdf', 'application/pdf',),
    'epub': ('epub', 'application/epub+zip',),
    }

def get_export(environ, start_response):
    """Retrieve an export file."""
    exports_dir = get_settings()['exports-directory']
    args = environ['wsgiorg.routing_args']
    ident_hash, type = args['ident_hash'], args['type']
    id, version = split_ident_hash(ident_hash)


    file_extension, mimetype = TYPE_INFO[type]
    filename = '{}-{}.{}'.format(id, version, file_extension)

    status = "200 OK"
    headers = [('Content-type', mimetype,),
               ('Content-disposition',
                'attached; filename={}'.format(filename),),
               ]
    start_response(status, headers)
    with open(os.path.join(exports_dir, filename), 'r') as file:
        return [file.read()]

MEDIA_TYPES = {
        'Collection': 'book',
        'Module': 'page',
        }

def search(environ, start_response):
    """Search API
    """
    params = cgi.parse_qs(environ.get('QUERY_STRING', ''))
    search_terms = params['q'][0]

    node_tree = grammar.parse(search_terms)
    search_dict = DictFormater().visit(node_tree)
    sort = [dict(search_dict)['sort']]

    db_query = DBQuery(search_dict)
    db_results = db_query()

    results = {}
    results['query'] = {
            'limits': [{i[0]: i[1]} for i in search_dict if i[0] != 'sort'],
            'sort': sort,
            }
    results['results'] = {'total': len(db_results), 'items': []}
    for i in db_results:
        results['results']['items'].append({
            'id': i[2],
            'type': MEDIA_TYPES.get(i[9], i[9]),
            'title': i[0],
            'authors': ['stub author'], # TODO not in db_results
            'keywords': ['stub keyword'], # TODO not in db_results
            'summarySnippet': 'stub summary snippet', # TODO not in db_results
            'bodySnippet': 'stub body snippet', # TODO not in db_results
            'pubDate': '2013-08-13T12:12Z', # TODO not in db_results
            })

    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    return [json.dumps(results)]
