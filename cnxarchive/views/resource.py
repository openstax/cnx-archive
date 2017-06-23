# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Resource Views."""
import logging

import psycopg2
import psycopg2.extras
from pyramid import httpexceptions
from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

from .. import config
from ..database import SQL

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
