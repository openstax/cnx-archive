# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import psycopg2

from . import get_settings
from .utils import split_ident_hash
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
            cursor.execute(SQL['get-module'], args)
            result = cursor.fetchone()[0]

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
            filename, mimetype, file = cursor.fetchone()

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
