# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import json
import psycopg2

from . import get_settings
from . import httpexceptions
from .utils import split_ident_hash, portaltype_to_mimetype
from .database import CONNECTION_SETTINGS_KEY, SQL


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
                query = SQL['get-tree-by-uuid-n-version']
                args = dict(id=result['id'], version=result['version'])
                cursor.execute(query, args)
                result['tree'] = cursor.fetchone()[0]
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

    if type not in TYPE_INFO:
        raise httpexceptions.HTTPNotFound()

    file_extension, mimetype = TYPE_INFO[type]
    filename = '{}-{}.{}'.format(id, version, file_extension)

    status = "200 OK"
    headers = [('Content-type', mimetype,),
               ('Content-disposition',
                'attached; filename={}'.format(filename),),
               ]
    try:
        with open(os.path.join(exports_dir, filename), 'r') as file:
            start_response(status, headers)
            return [file.read()]
    except IOError:
        raise httpexceptions.HTTPNotFound()
