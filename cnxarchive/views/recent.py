# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2018, Rice University
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
from ..utils import rfc822


logger = logging.getLogger('cnxarchive')


@view_config(route_name='recent', request_method='GET',
             renderer='templates/recent.rss',
             http_cache=(60, {'public': True}))
def recent(request):
    # setting the query variables
    num_entries = request.GET.get('number', 10)
    start_entry = request.GET.get('start', 0)
    portal_type = request.GET.get('type', ['Collection', 'Module'])
    if portal_type != ['Collection', 'Module']:
        portal_type = [portal_type]
    # search the database
    settings = request.registry.settings
    statement = """\
WITH recent_modules AS (
    SELECT
        name, revised, authors , abstract,
        ident_hash(uuid, major_version, minor_version) AS ident_hash
    FROM latest_modules NATURAL JOIN abstracts
    WHERE portal_type = ANY(%s)
    ORDER BY revised DESC
    LIMIT (%s)
    OFFSET (%s)
)
SELECT
    name,
    revised,
    (SELECT string_agg(u.full_name, ', ')
     FROM (SELECT unnest(authors) AS author) AS _authors
     JOIN users AS u ON (u.username = _authors.author)) as authors,
    abstract,
    ident_hash
FROM recent_modules;"""
    with db_connect() as db_c:
            with db_c.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(statement,
                            vars=(portal_type, num_entries, start_entry))
                latest_module_results = cur.fetchall()
    modules = []
    for module in latest_module_results:
        modules.append({
            'name': module['name'].decode('utf-8'),
            'revised': rfc822(module['revised']),
            'authors': module['authors'].decode('utf-8'),
            'abstract': module['abstract'].decode('utf-8'),
            'url': request.route_url('content',
                                     ident_hash=module['ident_hash']),
        })
    request.response.content_type = 'application/rss+xml'
    return {"latest_modules": modules}
