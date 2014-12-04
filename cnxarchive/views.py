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

from . import get_settings
from . import httpexceptions
from . import config
from . import cache
# FIXME double import
from . import database
from .database import SQL
from .search import (
    DEFAULT_PER_PAGE, QUERY_TYPES, DEFAULT_QUERY_TYPE,
    Query,
    )
from .sitemap import Sitemap
from .utils import (
    MODULE_MIMETYPE, COLLECTION_MIMETYPE, IdentHashSyntaxError,
    portaltype_to_mimetype,
    join_ident_hash, slugify, split_ident_hash, split_legacy_hash,
    )


logger = logging.getLogger('cnxarchive')


class ExportError(Exception):
    pass


# #################### #
#   Helper functions   #
# #################### #

def redirect_to_latest(cursor, id, path_format_string='/contents/{}@{}'):
    """Redirect to latest version of a module / collection using the provided
    path
    """
    cursor.execute(SQL['get-module-versions'], {'id': id})
    try:
        latest_version = cursor.fetchone()[0]
    except (TypeError, IndexError,): # None returned
        logger.debug("version was not supplied and could not be discovered.")
        raise httpexceptions.HTTPNotFound()
    raise httpexceptions.HTTPFound(
            path_format_string.format(id, latest_version))


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
    for line in get_settings()['exports-allowable-types'].splitlines():
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

    for type_name, type_info in TYPE_INFO:
        try:
            filename, mimetype, file_content = get_export_file(cursor,
                    id, version, type_name, exports_dirs)
            yield {
                'format': type_info['user_friendly_name'],
                'filename': filename,
                'details': type_info['description'],
                'path': u'/exports/{}@{}.{}/{}'.format(id, version, type_name,
                                                      filename),
                }
        except ExportError as e:
            # file not found, so don't include it
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
        raise httpexceptions.HTTPFound('/exports/{}@{}.{}'.format(
            id, latest_version, type))

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
                return (slugify_title_filename, mimetype, file.read())
        except IOError:
            # Let's see if the legacy file's there and make the new link if so
            #FIXME remove this code when we retire legacy
            try:
                with open(legacy_filepath, 'r') as file:
                    os.link(legacy_filepath,filepath)
                    return (slugify_title_filename, mimetype, file.read())
            except IOError as e:
                # to be handled by the else part below if unable to find file 
                # in any of the export dirs
                if not str(e).startswith('[Errno 2] No such file or directory:'):
                    logger.warn('IOError when accessing legacy export filepath:\n'
                                'exception: {}\n'
                                'filepath: {}\n'
                                .format(str(e), legacy_filepath))
    else:
        raise ExportError('{} not found'.format(filename))


HTML_WRAPPER = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>{}</body>
</html>
"""


def html_listify(tree, root_ul_element):
    for node in tree:
        li_elm = etree.SubElement(root_ul_element, 'li')
        a_elm = etree.SubElement(li_elm, 'a')
        a_elm.text = node['title']
        if node['id'] != 'subcol':
            # FIXME Hard coded route...
            a_elm.set('href', '/contents/{}.html'.format(node['id']))
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


def _get_content_json(environ=None, ident_hash=None, reqtype=None):
    """Helper that return a piece of content as a dict using the ident-hash (uuid@version)."""
    routing_args = environ and environ.get('wsgiorg.routing_args', {}) or {}
    settings = get_settings()
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
                if page_ident_hash:
                    page_ident_hash = ':{}'.format(page_ident_hash)
                path = '/contents/{{}}@{{}}{page_ident_hash}'.format(
                    page_ident_hash=page_ident_hash)
                if reqtype:
                    path = '{}.{}'.format(path, reqtype)
                    redirect_to_latest(cursor, id, path)
                else:
                    redirect_to_latest(cursor, id)
            result = get_content_metadata(id, version, cursor)
            if result['mediaType'] == COLLECTION_MIMETYPE:
                # Grab the collection tree.
                query = SQL['get-tree-by-uuid-n-version']
                args = dict(id=result['id'], version=result['version'])
                cursor.execute(query, args)
                tree = cursor.fetchone()[0]
                # Must unparse, otherwise we end up double encoding.
                result['tree'] = json.loads(tree)

                page_ident_hash = routing_args.get('page_ident_hash')
                if page_ident_hash:
                    for id_ in flatten_tree_to_ident_hashes(result['tree']):
                        uuid, version = split_ident_hash(id_)
                        if uuid == page_ident_hash or id_ == page_ident_hash:
                            raise httpexceptions.HTTPFound(
                                '/contents/{}'.format(
                                    join_ident_hash(uuid, version)))
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


# ######### #
#   Views   #
# ######### #

def get_content_json(environ, start_response):
    """Retrieve a piece of content as JSON using
    the ident-hash (uuid@version).
    """
    result = _get_content_json(environ=environ, reqtype='json')

    result = json.dumps(result)
    status = "200 OK"
    headers = [('Content-type', 'application/json',)]
    start_response(status, headers)
    return [result]


def get_content_html(environ, start_response):
    """Retrieve a piece of content as HTML using
    the ident-hash (uuid@version).
    """
    result = _get_content_json(environ=environ, reqtype='html')

    media_type = result['mediaType']
    if media_type == MODULE_MIMETYPE:
        content = result['content']
    elif media_type == COLLECTION_MIMETYPE:
        content = tree_to_html(result['tree'])

    status = "200 OK"
    headers = [('Content-type', 'application/xhtml+xml',)]
    start_response(status, headers)
    return [content]


def get_content(environ, start_response):
    """Retrieve a piece of content using the ident-hash (uuid@version).
    Depending on the HTTP_ACCEPT header return HTML or JSON.
    """
    if 'application/xhtml+xml' in environ.get('HTTP_ACCEPT', ''):
        return get_content_html(environ, start_response)

    else:
        return get_content_json(environ, start_response)


def redirect_legacy_content(environ, start_response):
    """Redirect from legacy /content/id/version url to new /contents/uuid@version.
       Handles collection context (book) as well
    """
    settings = get_settings()
    routing_args = environ['wsgiorg.routing_args']
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
                    raise httpexceptions.HTTPFound('/resources/{}/{}' \
                            .format(resourceid,filename))
                except TypeError:  # None returned
                    raise httpexceptions.HTTPNotFound()

    ident_hash = join_ident_hash(id, version)
    params = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
    if params.get('collection'): # page in book
        objid, objver = split_legacy_hash(params['collection'][0])
        book_uuid, book_version = _convert_legacy_id(objid, objver)
        if book_uuid:
            id, ident_hash = _get_page_in_book(
                    id, version, book_uuid, book_version)

    raise httpexceptions.HTTPFound('/contents/{}'.format(ident_hash))


def _convert_legacy_id(objid, objver=None):
    settings = get_settings()
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


def get_resource(environ, start_response):
    """Retrieve a file's data."""
    settings = get_settings()
    hash = environ['wsgiorg.routing_args']['hash']

    # Do the file lookup
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            args = dict(hash=hash)
            cursor.execute(SQL['get-resource'], args)
            try:
                mimetype, file = cursor.fetchone()
            except TypeError:  # None returned
                raise httpexceptions.HTTPNotFound()

    status = "200 OK"
    headers = [('Content-type', mimetype)]
    start_response(status, headers)
    return [file[:]]


def get_extra(environ, start_response):
    """Return information about a module / collection that cannot be cached
    """
    settings = get_settings()
    exports_dirs = settings['exports-directories'].split()
    args = environ['wsgiorg.routing_args']
    id, version = split_ident_hash(args['ident_hash'])
    results = {}

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            if not version:
                redirect_to_latest(cursor, id, '/extras/{}@{}')
            results['downloads'] = list(get_export_allowable_types(cursor,
                exports_dirs, id, version))
            results['isLatest'] = is_latest(cursor, id, version)
            results['canPublish'] = database.get_module_can_publish(cursor, id)

    headers = [('Content-type', 'application/json')]
    start_response('200 OK', headers)
    return [json.dumps(results)]


def get_export(environ, start_response):
    """Retrieve an export file."""
    settings = get_settings()
    exports_dirs = settings['exports-directories'].split()
    args = environ['wsgiorg.routing_args']
    ident_hash, type = args['ident_hash'], args['type']
    id, version = split_ident_hash(ident_hash)

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            try:
                filename, mimetype, file_content = get_export_file(cursor,
                        id, version, type, exports_dirs)
            except ExportError as e:
                logger.debug(str(e))
                raise httpexceptions.HTTPNotFound()

    status = "200 OK"
    headers = [('Content-type', mimetype,),
               ('Content-disposition',
                'attached; filename={}'.format(filename),),
               ]
    start_response(status, headers)
    return [file_content]


def search(environ, start_response):
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

    params = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
    try:
        search_terms = params.get('q', [])[0]
    except IndexError:
        start_response('200 OK', [('Content-type', 'application/json')])
        return [empty_response]
    query_type = params.get('t', None)
    if query_type is None or query_type not in QUERY_TYPES:
        query_type = DEFAULT_QUERY_TYPE

    try:
        per_page = int(params.get('per_page', [])[0])
    except (TypeError, ValueError, IndexError):
        per_page = None
    if per_page is None or per_page <= 0:
        per_page = DEFAULT_PER_PAGE
    try:
        page = int(params.get('page', [])[0])
    except (TypeError, ValueError, IndexError):
        page = None
    if page is None or page <= 0:
        page = 1

    query = Query.from_raw_query(search_terms)
    if not(query.filters or query.terms):
        start_response('200 OK', [('Content-type', 'application/json')])
        return [empty_response]
    db_results = cache.search(
            query, query_type,
            nocache=params.get('nocache', [''])[0].lower() == 'true')

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
            'id': '{}@{}'.format(record['id'],record['version']),
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

    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    return [json.dumps(results)]


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

def extras(environ, start_response):
    """Return a dict with archive metadata for webview
    """
    settings = get_settings()
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            metadata = {
                    'subjects': list(_get_subject_list(cursor)),
                    'featuredLinks': _get_featured_links(cursor),
                       }

    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    return [json.dumps(metadata)]


def sitemap(environ, start_response):
    """Return a sitemap xml file for search engines
    """
    settings = get_settings()
    xml = Sitemap()
    hostname = environ['HTTP_HOST']
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
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
            for r in res:
                xml.add_url('http://%s/contents/%s/%s' % (hostname,r[0], r[1]),
                            lastmod=r[2])

    status = '200 OK'
    headers = [('Content-type', 'text/xml')]
    start_response(status, headers)
    return [xml()]
