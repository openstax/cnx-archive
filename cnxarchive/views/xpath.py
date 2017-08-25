import json
import re
from urllib import urlencode

import psycopg2
import psycopg2.extras
from pyramid import httpexceptions
from lxml import etree
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from ..database import (
    SQL, get_tree)
from ..utils import (
    IdentHashShortId, IdentHashMissingVersion, IdentHashSyntaxError,
    split_ident_hash, COLLECTION_MIMETYPE, join_ident_hash
    )
from .content import HTML_WRAPPER
from .helpers import get_content_metadata, get_uuid, get_latest_version


# #################### #
#        Helpers       #
# #################### #


def xpath_book(request, uuid, version, return_json=True):
    """
    Given a request, book UUID and version:

    returns a JSON object or HTML list of results, each result containing:
    module_name,
    module_uuid,
    xpath_results, an array of strings, each an individual xpath result.
    """

    xpath_string = '{}/ancestor-or-self::*[@id][1]'.format(
        request.params.get('q'))
    results = execute_xpath(xpath_string, 'xpath', uuid, version)
    if return_json:
        return results
    else:
        return xpath_book_html(request, results)


def xpath_book_html(request, results):
    def remove_ns(text):
        return re.sub(' xmlns:?[a-z]*="[^"]*"', '', text)

    q = request.params.get('q', '')
    ul = etree.Element('ul')
    for item in results:
        li = etree.SubElement(ul, 'li')
        a = etree.SubElement(etree.SubElement(li, 'p'), 'a')
        a.set('href', '{}?{}'.format(
            request.route_path('xpath'),
            urlencode({'q': q, 'id': item['uuid']})))
        a.set('target', '_blank')
        a.text = item['name'].decode('utf-8')

        xpath_list = etree.SubElement(li, 'ul')
        for xpath_result in item['xpath_results']:
            li = etree.SubElement(xpath_list, 'li')
            elem = etree.fromstring(xpath_result)

            a = etree.SubElement(li, 'a')
            a.set('href', '{}#{}'.format(
                request.route_path('content-html', ident_hash=item['uuid']),
                elem.get('id')))
            a.set('target', '_blank')

            # get the exact element the user searched for
            m = elem.xpath(q)[0]
            a.text = u''.join(elem.xpath(q)[0].xpath('.//text()'))
            if not a.text.strip():
                # return the tag in xml
                a.text = remove_ns(etree.tostring(m, with_tail=False)
                                   .decode('utf-8'))

            etree.SubElement(li, 'p').text = remove_ns(
                xpath_result.decode('utf-8'))
    return HTML_WRAPPER.format(etree.tostring(ul))


def xpath_page(request, uuid, version):
    """Given a page UUID (and optional version), returns a JSON object of
    results, as in xpath_book()"""
    xpath_string = request.params.get('q')
    return execute_xpath(xpath_string, 'xpath-module', uuid, version)


def execute_xpath(xpath_string, sql_function, uuid, version):
    """Executes either xpath or xpath-module SQL function with given input
    params."""
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:

            try:
                cursor.execute(SQL[sql_function],
                               {'document_uuid': uuid,
                                'document_version': version,
                                'xpath_string': xpath_string})
            except psycopg2.Error as e:
                exc = httpexceptions.HTTPBadRequest()
                exc.explanation = e.pgerror
                raise exc

            for res in cursor.fetchall():
                yield {'name': res[0],
                       'uuid': res[1],
                       'xpath_results': res[2]}


# #################### #
#     Route method     #
# #################### #


@view_config(route_name='xpath', request_method='GET')
@view_config(route_name='xpath-json', request_method='GET')
def xpath(request):
    """View for the route. Determines UUID and version from input request
    and determines the type of UUID (collection or module) and executes
    the corresponding method."""
    ident_hash = request.params.get('id')
    xpath_string = request.params.get('q')

    if not ident_hash or not xpath_string:
        exc = httpexceptions.HTTPBadRequest
        exc.explanation = 'You must supply both a UUID and an xpath'
        raise exc

    try:
        uuid, version = split_ident_hash(ident_hash)
    except IdentHashShortId as e:
        uuid = get_uuid(e.id)
        version = e.version
    except IdentHashMissingVersion as e:
        uuid = e.id
        version = get_latest_version(e.id)
    except IdentHashSyntaxError:
        raise httpexceptions.HTTPBadRequest

    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            result = get_content_metadata(uuid, version, cursor)

    resp = request.response

    if result['mediaType'] == COLLECTION_MIMETYPE:
        matched_route = request.matched_route.name
        results = xpath_book(request, uuid, version,
                             return_json=matched_route.endswith('json'))
        if matched_route.endswith('json'):
            results = {'results': list(results)}
            resp.body = json.dumps(results)
            resp.content_type = 'application/json'
        else:
            resp.body = results
            resp.content_type = 'application/xhtml+xml'
    else:
        results = {'results': list(xpath_page(request, uuid, version))}
        resp.body = json.dumps(results)
        resp.content_type = 'application/json'

    resp.status = "200 OK"
    return resp
