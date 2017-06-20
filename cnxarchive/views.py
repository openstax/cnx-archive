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
from re import compile

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from . import config
from . import cache
# FIXME double import
from . import database
from .database import SQL, get_tree, get_collated_content
from .search import (
    DEFAULT_PER_PAGE, QUERY_TYPES, DEFAULT_QUERY_TYPE,
    Query,
    )
from .sitemap import Sitemap
from .robots import Robots
from .utils import (
    COLLECTION_MIMETYPE, IdentHashSyntaxError,
    IdentHashShortId, IdentHashMissingVersion,
    portaltype_to_mimetype, slugify, fromtimestamp,
    join_ident_hash, split_ident_hash, split_legacy_hash
    )


logger = logging.getLogger('cnxarchive')
_BLOCK_SIZE = 4096 * 64  # 256K

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']


class ExportError(Exception):
    """Used as catchall for other export errors."""

    pass


# #################### #
#   Helper functions   #
# #################### #

def get_uuid(shortid):
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-module-uuid'], {'id': shortid})
            try:
                return cursor.fetchone()[0]
            except (TypeError, IndexError,):  # None returned
                logger.debug("Short ID was supplied and could not discover "
                             "UUID.")
                raise httpexceptions.HTTPNotFound()


def get_latest_version(uuid_):
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL['get-module-versions'], {'id': uuid_})
            try:
                return cursor.fetchone()[0]
            except (TypeError, IndexError,):  # None returned
                raise httpexceptions.HTTPNotFound()




def is_latest(id, version):
    """Determine if this is the latest version of this content."""
    return get_latest_version(id) == version


LEGACY_EXTENSION_MAP = {'epub': 'epub', 'pdf': 'pdf', 'zip': 'complete.zip'}


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


def get_export_file(cursor, id, version, type, exports_dirs):
    """Retrieve file associated with document."""
    request = get_current_request()
    type_info = dict(request.registry.settings['_type_info'])

    if type not in type_info:
        raise ExportError("invalid type '{}' requested.".format(type))

    metadata = get_content_metadata(id, version, cursor)
    file_extension = type_info[type]['file_extension']
    mimetype = type_info[type]['mimetype']
    filename = '{}@{}.{}'.format(id, version, file_extension)
    legacy_id = metadata['legacy_id']
    legacy_version = metadata['legacy_version']
    legacy_filename = '{}-{}.{}'.format(
        legacy_id, legacy_version, LEGACY_EXTENSION_MAP[file_extension])
    slugify_title_filename = u'{}-{}.{}'.format(slugify(metadata['title']),
                                                version, file_extension)

    for exports_dir in exports_dirs:
        filepath = os.path.join(exports_dir, filename)
        legacy_filepath = os.path.join(exports_dir, legacy_filename)
        try:
            with open(filepath, 'r') as file:
                stats = os.fstat(file.fileno())
                modtime = fromtimestamp(stats.st_mtime)
                return (slugify_title_filename, mimetype,
                        stats.st_size, modtime, 'good', file.read())
        except IOError:
            # Let's see if the legacy file's there and make the new link if so
            # FIXME remove this code when we retire legacy
            try:
                with open(legacy_filepath, 'r') as file:
                    stats = os.fstat(file.fileno())
                    modtime = fromtimestamp(stats.st_mtime)
                    os.link(legacy_filepath, filepath)
                    return (slugify_title_filename, mimetype,
                            stats.st_size, modtime, 'good', file.read())
            except IOError as e:
                # to be handled by the else part below if unable to find file
                # in any of the export dirs
                if not str(e).startswith('[Errno 2] No such file or direct'):
                    logger.warn('IOError when accessing legacy export file:\n'
                                'exception: {}\n'
                                'filepath: {}\n'
                                .format(str(e), legacy_filepath))
    else:
        # No file, return "missing" state
        return (slugify_title_filename, mimetype, 0, None, 'missing', None)


HTML_WRAPPER = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>{}</body>
</html>
"""


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




def notblocked(page):
    """Determine if given url is a page that should be in sitemap."""
    for blocked in PAGES_TO_BLOCK:
        if blocked[0] != '*':
            blocked = '*' + blocked
        rx = compile(blocked.replace('*', '[^$]*'))
        if rx.match(page):
            return False
    return True


def _get_subject_list(cursor):
    """Return all subjects (tags) in the database except "internal" scheme."""
    subject = None
    last_tagid = None
    cursor.execute(SQL['get-subject-list'])
    for s in cursor.fetchall():
        tagid, tagname, portal_type, count = s

        if tagid != last_tagid:
            # It's a new subject, create a new dict and initialize count
            if subject:
                yield subject
            subject = {'id': tagid,
                       'name': tagname,
                       'count': {'module': 0, 'collection': 0}, }
            last_tagid = tagid

        if tagid == last_tagid and portal_type:
            # Just need to update the count
            subject['count'][portal_type.lower()] = count

    if subject:
        yield subject


def _get_available_languages_and_count(cursor):
    """Return a list of available language and its count"""
    cursor.execute(SQL['get-available-languages-and-count'])
    return cursor.fetchall()


def _get_featured_links(cursor):
    """Return featured books for the front page."""
    cursor.execute(SQL['get-featured-links'])
    return [i[0] for i in cursor.fetchall()]


def _get_service_state_messages(cursor):
    """Return a list of service messages."""
    cursor.execute(SQL['get-service-state-messages'])
    return [i[0] for i in cursor.fetchall()]


def _get_licenses(cursor):
    """Return a list of license info."""
    cursor.execute(SQL['get-license-info-as-json'])
    return [json_row[0] for json_row in cursor.fetchall()]





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


@view_config(route_name='content-extras', request_method='GET')
def get_extra(request):
    """Return information about a module / collection that cannot be cached."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    id, version = split_ident_hash(args['ident_hash'])
    results = {}

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            results['downloads'] = \
                list(get_export_allowable_types(cursor, exports_dirs,
                                                id, version))
            results['isLatest'] = is_latest(id, version)
            results['canPublish'] = database.get_module_can_publish(cursor, id)

    resp = request.response
    resp.content_type = 'application/json'
    resp.body = json.dumps(results)
    return resp


@view_config(route_name='export', request_method='GET')
def get_export(request):
    """Retrieve an export file."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    ident_hash, type = args['ident_hash'], args['type']
    id, version = split_ident_hash(ident_hash)

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            try:
                filename, mimetype, size, modtime, state, file_content = \
                    get_export_file(cursor, id, version, type, exports_dirs)
            except ExportError as e:
                logger.debug(str(e))
                raise httpexceptions.HTTPNotFound()

    if state == 'missing':
        raise httpexceptions.HTTPNotFound()

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = mimetype
    resp.content_disposition = u'attached; filename={}'.format(filename)
    resp.body = file_content
    return resp




@view_config(route_name='search', request_method='GET')
def search(request):
    """Search API."""
    empty_response = json.dumps({
        u'query': {
            u'limits': [],
            u'per_page': DEFAULT_PER_PAGE,
            u'page': 1,
            },
        u'results': {
            u'items': [],
            u'total': 0,
            u'limits': [],
            },
        })

    params = request.params
    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    search_terms = params.get('q', '')
    query_type = params.get('t', None)
    if query_type is None or query_type not in QUERY_TYPES:
        query_type = DEFAULT_QUERY_TYPE

    try:
        per_page = int(params.get('per_page', ''))
    except (TypeError, ValueError, IndexError):
        per_page = None
    if per_page is None or per_page <= 0:
        per_page = DEFAULT_PER_PAGE
    try:
        page = int(params.get('page', ''))
    except (TypeError, ValueError, IndexError):
        page = None
    if page is None or page <= 0:
        page = 1

    query = Query.from_raw_query(search_terms)
    if not(query.filters or query.terms):
        resp.body = empty_response
        return resp

    db_results = cache.search(
        query, query_type,
        nocache=params.get('nocache', '').lower() == 'true')

    authors = db_results.auxiliary['authors']
    # create a mapping for author id to index in auxiliary authors list
    author_mapping = {}
    for i, author in enumerate(authors):
        author_mapping[author['id']] = i

    results = {}
    limits = []
    for k, v in query.terms + query.filters:
        limits.append({'tag': k, 'value': v})
        if v in author_mapping:
            limits[-1]['index'] = author_mapping[v]
    results['query'] = {
        'limits': limits,
        'sort': query.sorts,
        'per_page': per_page,
        'page': page,
        }
    results['results'] = {'total': len(db_results), 'items': []}

    for record in db_results[((page - 1) * per_page):(page * per_page)]:
        results['results']['items'].append({
            'id': '{}@{}'.format(record['id'], record['version']),
            'mediaType': record['mediaType'],
            'title': record['title'],
            # provide the index in the auxiliary authors list
            'authors': [{
                'index': author_mapping[a['id']],
                'id': a['id'],
                } for a in record['authors']],
            'keywords': record['keywords'],
            'summarySnippet': record['abstract'],
            'bodySnippet': record['headline'],
            'pubDate': record['pubDate'],
            })
    result_limits = []
    for count_name, values in db_results.counts.items():
        if not values:
            continue
        result_limits.append({'tag': count_name,
                              'values': []})
        for keyword, count in values:
            value = {'value': keyword, 'count': count}
            # if it's an author, provide the index in auxiliary
            # authors list as well
            if keyword in author_mapping:
                value['index'] = author_mapping[keyword]
            result_limits[-1]['values'].append(value)
    results['results']['limits'] = result_limits
    # Add the supplemental result information.
    results['results']['auxiliary'] = db_results.auxiliary

    # In the case where a search is performed with an authorId
    # has a filter, it is possible for the database to return
    # no results even if the author exists in the database.
    #  Therefore, the database is queried a second time for
    # contact information associated with only the authorIds.
    #  The author information is then used to update the
    # results returned by the first database query.
    if len(db_results) <= 0:
        authors_results = []
        limits = results['query']['limits']
        index = 0
        settings = get_current_registry().settings
        connection = settings[config.CONNECTION_STRING]
        statement = SQL['get-users-by-ids']
        with psycopg2.connect(connection) as db_connection:
            with db_connection.cursor() as cursor:
                for idx, limit in enumerate(limits):
                    if limit['tag'] == 'authorID':
                        author = limit['value']
                        arguments = (author,)
                        cursor.execute(statement, arguments)
                        author_db_result = cursor.fetchall()
                        if author_db_result:
                            author_db_result = author_db_result[0][0]
                        else:
                            author_db_result = {'id': author, 'fullname': None}
                        authors_results.append(author_db_result)
                        limit['index'] = index
                        index = index + 1
                        limits[idx] = limit
        results['query']['limits'] = limits
        results['results']['auxiliary']['authors'] = authors_results

    resp.body = json.dumps(results)

    return resp


@view_config(route_name='extras', request_method='GET')
def extras(request):
    """Return a dict with archive metadata for webview."""
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            metadata = {
                'languages_and_count': _get_available_languages_and_count(
                    cursor),
                'subjects': list(_get_subject_list(cursor)),
                'featuredLinks': _get_featured_links(cursor),
                'messages': _get_service_state_messages(cursor),
                'licenses': _get_licenses(cursor),
                }

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    resp.body = json.dumps(metadata)
    return resp


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
