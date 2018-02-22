# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Content Views."""
import json
import logging

import psycopg2.extras

from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from ..database import (
    SQL, get_tree, get_collated_content, get_module_can_publish, db_connect)
from ..utils import (
    COLLECTION_MIMETYPE,
    IdentHashShortId, IdentHashMissingVersion,
    join_ident_hash, split_ident_hash,
    json_serial,
    )
from .helpers import get_uuid, get_latest_version, get_content_metadata
from .exports import get_export_file, ExportError

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

    with db_connect() as db_connection:
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
                            # 302 'cause lack of baked content may be temporary
                            raise httpexceptions.HTTPFound(request.route_path(
                                request.matched_route.name,
                                _query=request.params,
                                ident_hash=join_ident_hash(id, version),
                                ext=routing_args['ext']))
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


def get_content_json(request):
    """Retrieve content as JSON using the ident-hash (uuid@version)."""
    result = _get_content_json()

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/json'
    resp.body = json.dumps(result)
    return result, resp


def get_content_html(request):
    """Retrieve content as HTML using the ident-hash (uuid@version)."""
    result = _get_content_json()

    media_type = result['mediaType']
    if media_type == COLLECTION_MIMETYPE:
        content = tree_to_html(result['tree'])
    else:
        content = result['content']

    resp = request.response
    resp.body = content
    resp.status = "200 OK"
    resp.content_type = 'application/xhtml+xml'
    return result, resp


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
                    'content', ident_hash=node['id'], ext='.html'))
            else:
                a_elm.set('href', request.route_path(
                    'content',
                    separator=':',
                    ident_hash=parent_id,
                    page_ident_hash=node['id'],
                    ext='.html'))
        if 'contents' in node:
            elm = etree.SubElement(li_elm, 'ul')
            html_listify(node['contents'], elm, parent_id)


def is_latest(id, version):
    """Determine if this is the latest version of this content."""
    return get_latest_version(id) == version


def get_state(cursor, id, version):
    """Determine the state of the content."""
    args = join_ident_hash(id, version)
    sql_statement = """
    SELECT ms.statename
    FROM modules as m
    JOIN modulestates as ms
    ON m.stateid=ms.stateid
    WHERE ident_hash(uuid, major_version, minor_version) = %s
    """

    cursor.execute(sql_statement, vars=(args,))
    res = cursor.fetchone()
    if res is None:
        return None
    else:
        return res[0]


def get_export_allowable_types(cursor, exports_dirs, id, version):
    """Return export types."""
    request = get_current_request()

    for type_name, type_info in request.registry.settings['_type_info']:
        try:
            (filename, mimetype, file_size, file_created, state, file_content
             ) = get_export_file(cursor, id, version, type_name, exports_dirs)
            yield {
                'format': type_info['user_friendly_name'],
                'filename': filename,
                'size': file_size,
                'created': file_created and file_created.isoformat() or None,
                'state': state,
                'details': type_info['description'],
                'path': request.route_path(
                    'export', ident_hash=join_ident_hash(id, version),
                    type=type_name, ignore=u'/{}'.format(filename))
                }
        except ExportError as e:  # noqa
            # Some other problem, skip it
            pass


def get_books_containing_page(uuid, version):
    """Return a list of book names and UUIDs
    that contain a given module UUID."""

    with db_connect() as db_connection:
        with db_connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(SQL['get-books-containing-page'],
                           {'document_uuid': uuid,
                            'document_version': version})
            results = cursor.fetchall()
    return results

# ######### #
#   Views   #
# ######### #


@view_config(route_name='content', request_method='GET',
             http_cache=(3600000, {'public': True}))
def get_content(request):
    """Retrieve content using the ident-hash (uuid@version).

    Depending on extension or HTTP_ACCEPT header return HTML or JSON.
    """
    ext = request.matchdict.get('ext')
    accept = request.headers.get('ACCEPT', '')
    if not ext:
        if ('application/xhtml+xml' in accept):
            result, resp = get_content_html(request)
        else:  # default to json
            result, resp = get_content_json(request)
    elif ext == '.html':
        result, resp = get_content_html(request)
    elif ext == '.json':
        result, resp = get_content_json(request)
    else:
        raise httpexceptions.HTTPNotFound()

    if result['stateid'] not in [1, 8]:
        # state 1 = current, state 8 = fallback
        cc = resp.cache_control
        cc.prevent_auto = True
        cc.no_cache = True
        cc.no_store = True
        cc.must_revalidate = True
    else:
        resp.cache_control.public = True

    return resp


@view_config(route_name='content-extras', request_method='GET')
def get_extra(request):
    """Return information about a module / collection that cannot be cached."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    id, version = split_ident_hash(args['ident_hash'])
    results = {}
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            results['downloads'] = \
                list(get_export_allowable_types(cursor, exports_dirs,
                                                id, version))
            results['isLatest'] = is_latest(id, version)
            results['canPublish'] = get_module_can_publish(cursor, id)
            results['state'] = get_state(cursor, id, version)
            results['books'] = get_books_containing_page(id, version)
            formatAuthors(results['books'])

    resp = request.response
    resp.content_type = 'application/json'
    resp.body = json.dumps(results, default=json_serial)
    return resp


def formatAuthors(books):
    for book in books:
        for author in book['authors']:
            author['fullname'] = formatAuthorName(author)


def formatAuthorName(author):
    if author["fullname"]:
        return author["fullname"]
    flag = 0
    s = ""
    if author["title"]:
        flag += 1
        s += author["title"]
    if author['firstname']:
        flag += 1
        s += " " + author['firstname']
    if author['surname']:
        flag += 1
        s += " " + author['surname']
    if author['suffix']:
        s += " " + author['suffix']
    if flag >= 2:
        return s.strip()
    else:
        return author['username']
