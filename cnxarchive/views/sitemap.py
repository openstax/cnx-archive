# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Sitemap Views."""
import logging
from re import compile

import psycopg2
import psycopg2.extras
from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

from .. import config
from ..sitemap import Sitemap

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']

logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


def notblocked(page):
    """Determine if given url is a page that should be in sitemap."""
    for blocked in PAGES_TO_BLOCK:
        if blocked[0] != '*':
            blocked = '*' + blocked
        rx = compile(blocked.replace('*', '[^$]*'))
        if rx.match(page):
            return False
    return True


# ######### #
#   Views   #
# ######### #

@view_config(route_name='sitemap', request_method='GET')
def sitemap(request):
    """Return a sitemap xml file for search engines."""
    settings = get_current_registry().settings
    xml = Sitemap()
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            # FIXME
            # magic number limit comes from Google policy - will need to split
            # to multiple sitemaps before we have more content
            cursor.execute("""\
                    SELECT
                        ident_hash(uuid, major_version, minor_version)
                            AS idver,
                        REGEXP_REPLACE(TRIM(REGEXP_REPLACE(LOWER(name),
                            '[^0-9a-z]+', ' ', 'g')), ' +', '-', 'g'),
                        revised
                    FROM latest_modules
                    WHERE portal_type != 'CompositeModule'
                    ORDER BY revised DESC LIMIT 50000""")
            res = cursor.fetchall()
            for ident_hash, page_name, revised in res:
                url = request.route_url('content',
                                        ident_hash=ident_hash,
                                        ignore='/{}'.format(page_name))
                if notblocked(url):
                    xml.add_url(url, lastmod=revised)

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'text/xml'
    resp.body = xml()
    return resp
