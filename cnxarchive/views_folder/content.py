# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""All the views."""
import os
import json
import logging
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from .. import cache
# FIXME double import
from ..database import SQL, get_tree, get_collated_content
from ..utils import (
    COLLECTION_MIMETYPE,
    IdentHashShortId, IdentHashMissingVersion,
    portaltype_to_mimetype, fromtimestamp,
    join_ident_hash, split_ident_hash
    )

HTML_WRAPPER = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>{}</body>
</html>
"""

logger = logging.getLogger('cnxarchive')

# #################### #
#   Helper functions   #
# #################### #


def tree_to_html(tree):
    """Return html list version of book tree."""
    ul = etree.Element('ul')
    html_listify([tree], ul)
    return HTML_WRAPPER.format(etree.tostring(ul))


def _get_content_json(ident_hash=None):
    """Return a content as a dict from its ident-hash (uuid@version)."""
    request = get_current_request()
    routing_args = request and request.matchdict or {}
    settings = get_current_registry().settings
    if not ident_hash:
        ident_hash = routing_args['ident_hash']
    id, version = split_ident_hash(ident_hash)

    as_collated = asbool(request.GET.get('as_collated', True))
    page_ident_hash = routing_args.get('page_ident_hash', '')
    if page_ident_hash:
        try:
            p_id, p_version = split_ident_hash(page_ident_hash)
        except IdentHashShortId as e:
            p_id = get_uuid(e.id)
            p_version = e.version
        except IdentHashMissingVersion as e:
            # page ident hash doesn't need a version
            p_id = e.id
            p_version = None

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            result = get_content_metadata(id, version, cursor)
            if result['mediaType'] == COLLECTION_MIMETYPE:
                # Grab the collection tree.
                result['tree'] = get_tree(ident_hash, cursor,
                                          as_collated=as_collated)
                result['collated'] = as_collated
                if not result['tree']:
                    # If collated tree is not available, get the uncollated
                    # tree.
                    result['tree'] = get_tree(ident_hash, cursor)
                    result['collated'] = False

                if page_ident_hash:
                    for id_ in flatten_tree_to_ident_hashes(result['tree']):
                        id, version = split_ident_hash(id_)
                        if id == p_id and (
                           version == p_version or not p_version):
                            content = None
                            if as_collated:
                                content = get_collated_content(
                                    id_, ident_hash, cursor)
                            if content:
                                result = get_content_metadata(
                                    id, version, cursor)
                                result['content'] = content[:]
                                return result
                            raise httpexceptions.HTTPFound(request.route_path(
                                request.matched_route.name,
                                ident_hash=join_ident_hash(id, version)))
                    raise httpexceptions.HTTPNotFound()
            else:
                # Grab the html content.
                args = dict(id=id, version=result['version'],
                            filename='index.cnxml.html')
                cursor.execute(SQL['get-resource-by-filename'], args)
                try:
                    content = cursor.fetchone()[0]
                except (TypeError, IndexError,):  # None returned
                    logger.debug("module found, but "
                                 "'index.cnxml.html' is missing.")
                    raise httpexceptions.HTTPNotFound()
                result['content'] = content[:]

    return result


def get_content_metadata(id, version, cursor):
    """Return metadata related to the content from the database."""
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

        # FIXME We currently have legacy 'portal_type' names in the database.
        #       Future upgrades should replace the portal type with a mimetype
        #       of 'application/vnd.org.cnx.(module|collection|folder|<etc>)'.
        #       Until then we will do the replacement here.
        result['mediaType'] = portaltype_to_mimetype(result['mediaType'])

        return result
    except (TypeError, IndexError,):  # None returned
        raise httpexceptions.HTTPNotFound()


def html_listify(tree, root_ul_element, parent_id=None):
    """Recursively construct HTML nested list version of book tree.
    The original caller should not call this function with the
    `parent_id` defined.

    """
    request = get_current_request()
    is_first_node = parent_id is None
    if is_first_node:
        parent_id = tree[0]['id']
    for node in tree:
        li_elm = etree.SubElement(root_ul_element, 'li')
        a_elm = etree.SubElement(li_elm, 'a')
        a_elm.text = node['title']
        if node['id'] != 'subcol':
            if is_first_node:
                a_elm.set('href', request.route_path(
                    'content-html', ident_hash=node['id']))
            else:
                a_elm.set('href', request.route_path(
                    'content-html',
                    separator=':',
                    ident_hash=parent_id,
                    page_ident_hash=node['id']))
        if 'contents' in node:
            elm = etree.SubElement(li_elm, 'ul')
            html_listify(node['contents'], elm, parent_id)


# ######### #
#   Views   #
# ######### #


@view_config(route_name='content-json', request_method='GET')
def get_content_json(request):
    """Retrieve content as JSON using the ident-hash (uuid@version)."""
    result = _get_content_json()

    result = json.dumps(result)
    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/json'
    resp.body = result
    return resp


@view_config(route_name='content-html', request_method='GET')
def get_content_html(request):
    """Retrieve content as HTML using the ident-hash (uuid@version)."""
    result = _get_content_json()

    media_type = result['mediaType']
    if media_type == COLLECTION_MIMETYPE:
        content = tree_to_html(result['tree'])
    else:
        content = result['content']

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/xhtml+xml'
    resp.body = content
    return resp


@view_config(route_name='content', request_method='GET')
def get_content(request):
    """Retrieve content using the ident-hash (uuid@version).

    Depending on the HTTP_ACCEPT header return HTML or JSON.
    """
    if 'application/xhtml+xml' in request.headers.get('ACCEPT', ''):
        return get_content_html(request)

    else:
        return get_content_json(request)
