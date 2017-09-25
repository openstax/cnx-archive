# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Recent RSS feed View."""
import logging

import psycopg2.extras
from pyramid.view import view_config

from .. import config
from ..database import db_connect

logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


def format_author(personids, settings):
    """
    Takes a list of personid's and searches in the persons table to get their
    full names and returns a list of the full names as a string.
    """
    statement = """
                SELECT fullname
                FROM persons
                WHERE personid = ANY (%s);
                """
    with db_connect() as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(statement, vars=(personids,))
                authors_list = cursor.fetchall()
    return ', '.join([author[0] for author in authors_list]).decode('utf-8')


def html_rss_date(datetime):
    """
    Return the HTTP-date format of python's datetime time.

    Based on:
    https://legacy.cnx.org/content/recent.rss
    """
    return datetime.strftime("%a, %d %b %Y %H:%M:%S %z")


# #################### #
#         Views        #
# #################### #


@view_config(route_name='recent', request_method='GET',
             renderer='templates/recent.rss')
def recent(request):
    # setting the query variables
    num_entries = request.GET.get('number', 10)
    start_entry = request.GET.get('start', 0)
    portal_type = request.GET.get('type', ['Collection', 'Module'])
    if portal_type != ['Collection', 'Module']:
        portal_type = [portal_type]
    # search the database
    settings = request.registry.settings
    statement = """
                SELECT name, revised, authors, abstract, uuid
                FROM latest_modules
                JOIN abstracts
                ON latest_modules.abstractid = abstracts.abstractid
                WHERE portal_type = ANY (%s)
                ORDER BY revised DESC
                LIMIT (%s) OFFSET (%s);
                """
    with db_connect() as db_c:
            with db_c.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(statement,
                            vars=(portal_type, num_entries, start_entry))
                latest_modules = cur.fetchall()
    for module in latest_modules:
        module['revised'] = html_rss_date(module['revised'])
        module['authors'] = format_author(module['authors'], settings)
        module['abstract'] = module['abstract'].decode('utf-8')
        module['name'] = module['name'].decode('utf-8')
        module['uuid'] = request.route_url('content',
                                           ident_hash=module['uuid'])
    request.response.content_type = 'application/rss+xml'
    return {"latest_modules": latest_modules}
