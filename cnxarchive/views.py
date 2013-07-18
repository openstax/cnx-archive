# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import psycopg2

from . import get_settings
from .utils import split_ident_hash
from .database import CONNECTION_SETTINGS_KEY, SQL


def get_content(environ, start_response):
    """Retrieve a piece of content using the ident-hash (uuid@version)."""
    settings = get_settings()
    ident_hash = environ['app.matchdict']['ident-hash']
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
