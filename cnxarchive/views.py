# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import json
import logging
import psycopg2
import urlparse

from lxml import etree
from cnxquerygrammar.query_parser import grammar, DictFormater
from cnxepub.models import flatten_tree_to_ident_hashes
from datetime import datetime, timedelta
from pytz import timezone
from re import compile
from pyramid import httpexceptions
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from . import config
from . import cache
# FIXME double import
from . import database
from .database import SQL, get_tree, SQL_DIRECTORY
from .search import (
    DEFAULT_PER_PAGE, QUERY_TYPES, DEFAULT_QUERY_TYPE,
    Query,
    )
from .sitemap import Sitemap
from .robots import Robots
from .utils import (
    MODULE_MIMETYPE, COLLECTION_MIMETYPE, IdentHashSyntaxError,
    portaltype_to_mimetype,
    join_ident_hash, slugify, split_ident_hash, split_legacy_hash, fromtimestamp
    )


logger = logging.getLogger('cnxarchive')

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']


class ExportError(Exception):
    pass


# #################### #
#   Helper functions   #
# #################### #

def redirect_to_latest(cursor, id, route_name='content', route_args=None):
    """Redirect to latest version of a module / collection using the provided
    path
    """
    cursor.execute(SQL['get-module-versions'], {'id': id})
    try:
        latest_version = cursor.fetchone()[0]
    except (TypeError, IndexError,): # None returned
        logger.debug("version was not supplied and could not be discovered.")
        raise httpexceptions.HTTPNotFound()

    if route_args is None:
        route_args = {}
    request = get_current_request()
    route_args['ident_hash'] = join_ident_hash(id, latest_version)
    raise httpexceptions.HTTPFound(request.route_path(
        route_name, **route_args))


def get_content_metadata(id, version, cursor):
    """Return metadata related to the content from the database
    """
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


def is_latest(cursor, id, version):
    cursor.execute(SQL['get-module-versions'], {'id': id})
    try:
        latest_version = cursor.fetchone()[0]
        return latest_version == version
    except (TypeError, IndexError,): # None returned
        raise httpexceptions.HTTPNotFound()


TYPE_INFO = []
LEGACY_EXTENSION_MAP = {'epub':'epub','pdf':'pdf','zip':'complete.zip'}
def get_type_info():
    if TYPE_INFO:
        return
    settings = get_current_registry().settings
    for line in settings['exports-allowable-types'].splitlines():
        if not line.strip():
            continue
        type_name, type_info = line.strip().split(':', 1)
        type_info = type_info.split(',', 3)
        TYPE_INFO.append((type_name, {
            'type_name': type_name,
            'file_extension': type_info[0],
            'mimetype': type_info[1],
            'user_friendly_name': type_info[2],
            'description': type_info[3],
            }))


def get_export_allowable_types(cursor, exports_dirs, id, version):
    """Return export types
    """
    get_type_info()
    request = get_current_request()

    for type_name, type_info in TYPE_INFO:
        try:
            filename, mimetype, file_size, file_created, state, file_content = get_export_file(cursor,
                    id, version, type_name, exports_dirs)
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
        except ExportError as e:
            # Some other problem, skip it
            pass


def get_export_file(cursor, id, version, type, exports_dirs):
    get_type_info()
    type_info = dict(TYPE_INFO)

    if type not in type_info:
        raise ExportError("invalid type '{}' requested.".format(type))

    if not version:
        cursor.execute(SQL['get-module-versions'], {'id': id})
        try:
            latest_version = cursor.fetchone()[0]
        except (TypeError, IndexError,): # None returned
            raise ExportError("version was not supplied and could not be "
                    "discovered.")
        request = get_current_request()
        raise httpexceptions.HTTPFound(
            request.route_path('export',
                               ident_hash=join_ident_hash(id, latest_version),
                               type=type))

    metadata = get_content_metadata(id, version, cursor)
    file_extension = type_info[type]['file_extension']
    mimetype = type_info[type]['mimetype']
    filename = '{}@{}.{}'.format(id, version, file_extension)
    legacy_id = metadata['legacy_id']
    legacy_version = metadata['legacy_version']
    legacy_filename = '{}-{}.{}'.format(legacy_id, legacy_version, 
            LEGACY_EXTENSION_MAP[file_extension])
    slugify_title_filename = u'{}-{}.{}'.format(slugify(metadata['title']),
            version, file_extension)

    for exports_dir in exports_dirs:
        filepath = os.path.join(exports_dir, filename)
        legacy_filepath = os.path.join(exports_dir, legacy_filename)
        try:
            with open(filepath, 'r') as file:
                stats = os.fstat(file.fileno())
                modtime = fromtimestamp(stats.st_mtime)
                return (slugify_title_filename, mimetype, stats.st_size, modtime, 'good', file.read())
        except IOError:
            # Let's see if the legacy file's there and make the new link if so
            #FIXME remove this code when we retire legacy
            try:
                with open(legacy_filepath, 'r') as file:
                    stats = os.fstat(file.fileno())
                    modtime = fromtimestamp(stats.st_mtime)
                    os.link(legacy_filepath,filepath)
                    return (slugify_title_filename, mimetype, stats.st_size, modtime,'good', file.read())
            except IOError as e:
                # to be handled by the else part below if unable to find file 
                # in any of the export dirs
                if not str(e).startswith('[Errno 2] No such file or directory:'):
                    logger.warn('IOError when accessing legacy export filepath:\n'
                                'exception: {}\n'
                                'filepath: {}\n'
                                .format(str(e), legacy_filepath))
    else:
        #No file, return "missing" state
        return (slugify_title_filename, mimetype, 0, None, 'missing', None)


HTML_WRAPPER = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>{}</body>
</html>
"""


def html_listify(tree, root_ul_element):
    request = get_current_request()
    for node in tree:
        li_elm = etree.SubElement(root_ul_element, 'li')
        a_elm = etree.SubElement(li_elm, 'a')
        a_elm.text = node['title']
        if node['id'] != 'subcol':
            a_elm.set('href', request.route_path(
                'content-html', ident_hash=node['id']))
        if 'contents' in node:
            elm = etree.SubElement(li_elm, 'ul')
            html_listify(node['contents'], elm)


def tree_to_html(tree):
    ul = etree.Element('ul')
    html_listify([tree], ul)
    return HTML_WRAPPER.format(etree.tostring(ul))


def _get_page_in_book(page_uuid, page_version, book_uuid, book_version, latest=False):
    book_ident_hash = join_ident_hash(book_uuid, book_version)
    coltree = _get_content_json(ident_hash=book_ident_hash)['tree']
    pages = list(flatten_tree_to_ident_hashes(coltree))
    page_ident_hash = join_ident_hash(page_uuid, page_version)
    if page_ident_hash in pages:
        return book_uuid, '{}:{}'.format(
                latest and book_uuid or book_ident_hash, page_uuid)
    # book not in page
    return page_uuid, page_ident_hash


def _get_content_json(request=None, ident_hash=None, reqtype=None):
    """Helper that return a piece of content as a dict using the ident-hash (uuid@version)."""
    routing_args = request and request.matchdict or {}
    settings = get_current_registry().settings
    if not ident_hash:
        ident_hash = routing_args['ident_hash']
    try:
        id, version = split_ident_hash(ident_hash)
    except IdentHashSyntaxError:
        raise httpexceptions.HTTPNotFound()

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                page_ident_hash = routing_args.get('page_ident_hash', '')

                route_name = 'content'
                route_args = {}
                if page_ident_hash:
                    route_args['separator'] = ':'
                    route_args['page_ident_hash'] = page_ident_hash
                if reqtype:
                    route_name = 'content-{}'.format(reqtype)
                redirect_to_latest(cursor, id, route_name=route_name,
                                   route_args=route_args)

            result = get_content_metadata(id, version, cursor)
            if result['mediaType'] == COLLECTION_MIMETYPE:
                # Grab the collection tree.
                result['tree'] = get_tree(ident_hash, cursor)

                page_ident_hash = routing_args.get('page_ident_hash')
                if page_ident_hash:
                    for id_ in flatten_tree_to_ident_hashes(result['tree']):
                        uuid, version = split_ident_hash(id_)
                        if uuid == page_ident_hash or id_ == page_ident_hash:
                            raise httpexceptions.HTTPFound(request.route_path(
                                'content',
                                ident_hash=join_ident_hash(uuid, version)))
                    raise httpexceptions.HTTPNotFound()
            else:
                # Grab the html content.
                args = dict(id=id, version=result['version'],
                            filename='index.cnxml.html')
                cursor.execute(SQL['get-resource-by-filename'], args)
                try:
                    content = cursor.fetchone()[0]
                except (TypeError, IndexError,):  # None returned
                    logger.debug("module found, but 'index.cnxml.html' is missing.")
                    raise httpexceptions.HTTPNotFound()
                result['content'] = content[:]

    return result


def html_date(datetime):
    """
    Returns the HTTP-date format of python's datetime time as per:
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    """
    return datetime.strftime("%a, %d %b %Y %X %Z")


def notblocked(page):
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


@view_config(route_name='content-json', request_method='GET')
def get_content_json(request):
    """Retrieve a piece of content as JSON using
    the ident-hash (uuid@version).
    """
    result = _get_content_json(request=request, reqtype='json')

    result = json.dumps(result)
    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/json'
    resp.body = result
    return resp


@view_config(route_name='content-html', request_method='GET')
def get_content_html(request):
    """Retrieve a piece of content as HTML using
    the ident-hash (uuid@version).
    """
    result = _get_content_json(request=request, reqtype='html')

    media_type = result['mediaType']
    if media_type == MODULE_MIMETYPE:
        content = result['content']
    elif media_type == COLLECTION_MIMETYPE:
        content = tree_to_html(result['tree'])

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/xhtml+xml'
    resp.body = content
    return resp


@view_config(route_name='content', request_method='GET')
def get_content(request):
    """Retrieve a piece of content using the ident-hash (uuid@version).
    Depending on the HTTP_ACCEPT header return HTML or JSON.
    """
    if 'application/xhtml+xml' in request.headers.get('ACCEPT', ''):
        return get_content_html(request)

    else:
        return get_content_json(request)


@view_config(route_name='legacy-redirect', request_method='GET')
@view_config(route_name='legacy-redirect-latest', request_method='GET')
@view_config(route_name='legacy-redirect-w-version', request_method='GET')
def redirect_legacy_content(request):
    """Redirect from legacy /content/id/version url to new /contents/uuid@version.
       Handles collection context (book) as well
    """
    settings = get_current_registry().settings
    routing_args = request.matchdict
    objid = routing_args['objid']
    objver = routing_args.get('objver')
    filename = routing_args.get('filename')

    id, version = _convert_legacy_id(objid, objver)

    if not id:
        raise httpexceptions.HTTPNotFound()

    if filename:
        with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
            with db_connection.cursor() as cursor:
                args = dict(id=id, version=version, filename=filename)
                cursor.execute(SQL['get-resourceid-by-filename'], args)
                try:
                    res = cursor.fetchone()
                    resourceid = res[0]
                    raise httpexceptions.HTTPFound(request.route_path(
                        'resource', hash=resourceid,
                        ignore=u'/{}'.format(filename)))
                except TypeError:  # None returned
                    raise httpexceptions.HTTPNotFound()

    ident_hash = join_ident_hash(id, version)
    params = request.params
    if params.get('collection'): # page in book
        objid, objver = split_legacy_hash(params['collection'])
        book_uuid, book_version = _convert_legacy_id(objid, objver)
        if book_uuid:
            id, ident_hash = _get_page_in_book(
                    id, version, book_uuid, book_version)

    raise httpexceptions.HTTPFound(
        request.route_path('content', ident_hash=ident_hash))


def _convert_legacy_id(objid, objver=None):
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            if objver:
                args = dict(objid=objid, objver=objver)
                cursor.execute(SQL['get-content-from-legacy-id-ver'], args)
            else:
                cursor.execute(SQL['get-content-from-legacy-id'], dict(objid=objid))
            try:
                id, version = cursor.fetchone()
                return (id, version)
            except TypeError:  # None returned
                return (None, None)


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
    """Return information about a module / collection that cannot be cached
    """
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    id, version = split_ident_hash(args['ident_hash'])
    results = {}

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                redirect_to_latest(cursor, id, 'content-extras')
            results['downloads'] = list(get_export_allowable_types(cursor,
                exports_dirs, id, version))
            results['isLatest'] = is_latest(cursor, id, version)
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
                filename, mimetype, size, modtime, state, file_content = get_export_file(cursor,
                        id, version, type, exports_dirs)
            except ExportError as e:
                logger.debug(str(e))
                raise httpexceptions.HTTPNotFound()

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = mimetype
    resp.content_disposition = u'attached; filename={}'.format(filename)
    resp.body = file_content
    return resp


@view_config(route_name='in-book-search', request_method='GET')
def in_book_search(request):
    """ Full text, in-book search """
    results = {}

    args = request.matchdict
    ident_hash = args['ident_hash']
    args['ident_hash'] = args['ident_hash'].split('@')[0]

    try:
        args['search_term'] = request.params.get('q', '')
    except (TypeError, ValueError, IndexError):
        args['search_term'] = None

    id, version = split_ident_hash(ident_hash)
    if version:
        if '.' in version:
            args['major_version'], args['minor_version'] = [int(v) for v in version.split('.')]
        else:
            args['major_version'] = int(version)
            args['minor_version'] = None

    settings = get_current_registry().settings
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                redirect_to_latest(cursor, id, 'in-book-search', route_args=request.params.copy())

            sql_file = os.path.join(SQL_DIRECTORY, 'get-in-book-search.sql')
            with open(sql_file, 'r') as fp:
                cursor.execute(fp.read(), args)
                res = cursor.fetchall()
                results['results'] = {'total': len(res), 'query': [args], 'items': []}

                # Build the result dict
                for uuid, version, title, headline, rank in res:
                    results['results']['items'].append({
                        'rank': '{}'.format(rank),
                        'uuid': '{}'.format(uuid),
                        'version': '{}'.format(version),
                        'title': '{}'.format(title),
                        'headline': '{}'.format(headline),
                    })

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    resp.body = json.dumps(results)

    return resp


@view_config(route_name='search', request_method='GET')
def search(request):
    """Search API
    """
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
    try:
        search_terms = params.get('q', '')
    except IndexError:
        resp.body = empty_response
        return resp
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


def _get_subject_list(cursor):
    """Return all subjects (tags) in the database except "internal" scheme
    """
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
                       'count': {'module': 0, 'collection': 0},
                      }
            last_tagid = tagid

        if tagid == last_tagid and portal_type:
            # Just need to update the count
            subject['count'][portal_type.lower()] = count

    if subject:
        yield subject


def _get_featured_links(cursor):
    """Return featured books for the front page"""
    cursor.execute(SQL['get-featured-links'])
    return [i[0] for i in cursor.fetchall()]


def _get_service_state_messages(cursor):
    """Returns a list of service messages."""
    cursor.execute(SQL['get-service-state-messages'])
    return [i[0] for i in cursor.fetchall()]


def _get_licenses(cursor):
    """Return a list of license info."""
    cursor.execute(SQL['get-license-info-as-json'])
    return [json_row[0] for json_row in cursor.fetchall()]


@view_config(route_name='extras', request_method='GET')
def extras(request):
    """Return a dict with archive metadata for webview
    """
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            metadata = {
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
    """Return a sitemap xml file for search engines
    """
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
                        uuid||'@'||concat_ws('.',major_version,minor_version) AS idver,
                        REGEXP_REPLACE(TRIM(REGEXP_REPLACE(LOWER(name), '[^0-9a-z]+', ' ', 'g')), ' +', '-', 'g'),
                        revised
                    FROM latest_modules
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


@view_config(route_name='robots', request_method='GET')
def robots(request):
    """
    Returns a robots.txt file
    """
    robots_dot_txt = Robots(sitemap=request.route_url('sitemap'))

    bot_delays = {
        '*': '',
        'ScoutJet': '10',
        'Baiduspider': '10',
        'BecomeBot': '20',
        'Slurp': '10'
        }

    for bot, delay in bot_delays.iteritems():
        robots_dot_txt.add_bot(bot, delay, PAGES_TO_BLOCK)

    gmt = timezone('GMT')
    # it expires in 5 days
    exp_time = datetime.now(gmt) + timedelta(5)

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'text/plain'
    resp.cache_control = 'max-age=36000, must-revalidate'
    resp.last_modified = html_date(datetime.now(gmt))
    resp.expires = html_date(exp_time)
    resp.body = robots_dot_txt.to_string()
    return resp
