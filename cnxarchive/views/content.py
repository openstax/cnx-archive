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
import re

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
from .helpers import (
    get_uuid, get_latest_version, get_head_version, get_content_metadata
    )
from .exports import get_export_files

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

    as_collated = asbool(request.GET.get('as_collated', True))
    page_ident_hash = routing_args.get('page_ident_hash', '')
    p_id, p_version = (None, None)
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

    id, version = split_ident_hash(ident_hash, containing=p_id)

    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            result = get_content_metadata(id, version, cursor)
            # Build url for canonical link header
            result['canon_url'] = get_canonical_url(result, request)

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
                                # Build url for canonical link header
                                result['canon_url'] = (
                                        get_canonical_url(result, request))
                                result['content'] = content[:]
                                return result
                            # 302 'cause lack of baked content may be temporary
                            raise httpexceptions.HTTPFound(request.route_path(
                                request.matched_route.name,
                                _query=request.params,
                                ident_hash=join_ident_hash(id, version),
                                ext=routing_args['ext']),
                                headers=[("Cache-Control",
                                          "max-age=60, public")])
                    raise httpexceptions.HTTPNotFound()
            else:
                result = get_content_metadata(id, version, cursor)
                # Build url for canonical link header
                result['canon_url'] = get_canonical_url(result, request)
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

    if '<head>' in content:
        content = content.replace(
            '</head>',
            '<meta name="robots" content="noindex"/></head>', 1)
    else:
        content = content.replace(
            '<body',
            '<head><meta name="robots" content="noindex"/></head><body', 1)

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
    type_settings = request.registry.settings['_type_info']
    type_names = [k for k, v in type_settings]
    type_infos = [v for k, v in type_settings]
    # We took the type_names directly from the setting this function uses to
    # check for valid types, so it should never raise an ExportError here
    file_tuples = get_export_files(cursor, id, version, type_names,
                                   exports_dirs, read_file=False)
    type_settings = dict(type_settings)
    for filename, mimetype, file_size, file_created, state, file_content \
            in file_tuples:
        type_name = filename.rsplit('.', 1)[-1]
        type_info = type_settings[type_name]
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


# NOTE: Expects both a normal cursor and a RealDictCursor
def get_book_info(cursor, real_dict_cursor, book_id,
                  book_version, page_id, page_version):
    """Return information about a given book.

    Return the book's title, id, shortId, authors and revised date.
    Raise HTTPNotFound if the page is not in the book.
    """
    book_ident_hash = join_ident_hash(book_id, book_version)
    page_ident_hash = join_ident_hash(page_id, page_version)
    tree = get_tree(book_ident_hash, cursor)

    # Check if the page appears in the book tree
    if not tree or page_ident_hash not in flatten_tree_to_ident_hashes(tree):
        # Return a 404 error if the page is not actually in the book tree
        raise httpexceptions.HTTPNotFound()

    sql_statement = """
    SELECT m.name as title,
           ident_hash(m.uuid, m.major_version, m.minor_version)
           as ident_hash,
           short_ident_hash(m.uuid, m.major_version, m.minor_version)
           as shortId, ARRAY(
               SELECT row_to_json(user_row)
               FROM (
                   SELECT u.username, u.first_name as firstname,
                        u.last_name as surname, u.full_name as fullname,
                        u.title, u.suffix
               ) as user_row
           ) as authors,
           m.revised
    FROM modules m
    JOIN users as u on u.username = ANY(m.authors)
    WHERE ident_hash(m.uuid, m.major_version, m.minor_version) = %s
    """
    real_dict_cursor.execute(sql_statement, vars=(book_ident_hash,))
    return real_dict_cursor.fetchone()


# NOTE: Expects a normal cursor
def get_portal_type(cursor, id, version):
    """Return the module's portal_type."""
    args = join_ident_hash(id, version)
    sql_statement = """
    SELECT m.portal_type
    FROM modules as m
    WHERE ident_hash(uuid, major_version, minor_version) = %s
    """

    cursor.execute(sql_statement, vars=(args,))
    res = cursor.fetchone()
    if res is None:
        return None
    else:
        return res[0]


def get_books_containing_page(cursor, uuid, version,
                              context_uuid=None, context_version=None):
    """Return a list of book names and UUIDs
    that contain a given module UUID."""
    with db_connect() as db_connection:
        # Uses a RealDictCursor instead of the regular cursor
        with db_connection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as real_dict_cursor:
            # In the future the books-containing-page SQL might handle
            # all of these cases. For now we branch the code out in here.
            if context_uuid and context_version:
                return [get_book_info(cursor, real_dict_cursor, context_uuid,
                                      context_version, uuid, version)]
            else:
                portal_type = get_portal_type(cursor, uuid, version)
                if portal_type == 'Module':
                    real_dict_cursor.execute(SQL['get-books-containing-page'],
                                             {'document_uuid': uuid,
                                              'document_version': version})
                    return real_dict_cursor.fetchall()
                else:
                    # Books are currently not in any other book
                    return []


def get_canonical_url(metadata, request):
    """Builds canonical in book url from a pages metadata."""
    slug_title = u'/{}'.format('-'.join(metadata['title'].split()))
    settings = get_current_registry().settings

    canon_host = settings.get('canonical-hostname',
                              re.sub('archive.', '', request.host))
    if metadata['canonical'] is None:
        canon_url = request.route_url(
                'content',
                ident_hash=metadata['id'],
                ignore=slug_title)
    else:
        canon_url = request.route_url(
                'content',
                ident_hash=metadata['canonical'],
                separator=':',
                page_ident_hash=metadata['id'],
                ignore=slug_title)

    return re.sub(request.host, canon_host, canon_url)

# ######### #
#   Views   #
# ######### #


@view_config(route_name='content', request_method='GET',
             http_cache=(31536000, {'public': True}))
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

    # Build the canonical link
    resp.headerlist.append(
            ('Link', '<{}> ;rel="Canonical"'.format(result['canon_url'])))

    return resp


@view_config(route_name='content-extras', request_method='GET',
             http_cache=(600, {'public': True}))
def get_extra(request):
    """Return information about a module / collection that cannot be cached."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    if args['page_ident_hash']:
        context_id, context_version = split_ident_hash(args['ident_hash'])
        try:
            id, version = split_ident_hash(args['page_ident_hash'])
        except IdentHashShortId as e:
            id = get_uuid(e.id)
            version = e.version
        except IdentHashMissingVersion as e:
            # Ideally we would find the page version
            # that is in the book instead of latest
            id = e.id
            version = get_latest_version(e.id)
    else:
        context_id = context_version = None
        id, version = split_ident_hash(args['ident_hash'])
    results = {}
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            results['downloads'] = \
                list(get_export_allowable_types(cursor, exports_dirs,
                                                id, version))
            results['isLatest'] = is_latest(id, version)
            results['latestVersion'] = get_latest_version(id)
            results['headVersion'] = get_head_version(id)
            results['canPublish'] = get_module_can_publish(cursor, id)
            results['state'] = get_state(cursor, id, version)
            results['books'] = get_books_containing_page(cursor, id, version,
                                                         context_id,
                                                         context_version)
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
