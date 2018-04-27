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

from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

from .. import config
from ..database import db_connect
from ..sitemap import Sitemap, SitemapIndex

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']

# According to https://www.sitemaps.org/faq.html#faq_sitemap_size, a sitemap
# file cannot have more than 50,000 urls and cannot exceed 50MB.
SITEMAP_LIMIT = 50000

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
    xml = Sitemap()
    from_id = request.matchdict.get('from_id')
    if from_id is not None:
        fromlimit = 'AND module_ident <= {}'.format(from_id)
    else:
        fromlimit = ''
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute("""\
                SELECT
                    ident_hash(uuid, major_version, minor_version)
                        AS idver,
                    REGEXP_REPLACE(TRIM(REGEXP_REPLACE(LOWER(name),
                        '[^0-9a-z]+', ' ', 'g')), ' +', '-', 'g'),
                    revised
                FROM latest_modules
                WHERE portal_type NOT IN ('CompositeModule', 'SubCollection')
                  {}
                ORDER BY module_ident DESC
                LIMIT {}""".format(fromlimit, SITEMAP_LIMIT))
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


@view_config(route_name='sitemap-index', request_method='GET')
def sitemap_index(request):
    """Return a sitemap index xml file for search engines."""
    sitemaps = []
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute("""\
                SELECT t.module_ident
                FROM (
                  SELECT module_ident,
                         row_number() OVER (ORDER BY module_ident DESC) AS row
                  FROM latest_modules
                  WHERE portal_type NOT IN (
                      'CompositeModule', 'SubCollection')
                ) AS t
                WHERE t.row % {} = 1""".format(SITEMAP_LIMIT))

            for (module_ident,) in cursor.fetchall():
                sitemaps.append(Sitemap(url=request.route_url(
                    'sitemap', from_id=module_ident)))

    si = SitemapIndex(sitemaps=sitemaps)
    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'text/xml'
    resp.body = si()
    return resp
