import json
import psycopg2
import psycopg2.extras
from pyramid import httpexceptions
from lxml import etree
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config
from .content import _get_content_json, HTML_WRAPPER
from .helpers import get_content_metadata

from .. import config
from ..database import (
    SQL, get_tree)
from ..utils import (
    IdentHashShortId, IdentHashMissingVersion, IdentHashSyntaxError,
    split_ident_hash, COLLECTION_MIMETYPE, join_ident_hash
    )
from .helpers import get_uuid, get_latest_version


# #################### #
#        Helpers       #
# #################### #


def xpath_book(request, uuid, version, return_json=True):
    """
    Given a request, book UUID and version:

    if return_json is False, returns the HTML tree
    of the book, with each module title a link which returns the xpath query
    result for that page UUID (and version if supplied, else uses most recent),
    or

    otherwise, returns a JSON object of results, each result containing:
    module_name,
    module_uuid,
    xpath_results, an array of strings, each an individual xpath result.
    """

    xpath_string = request.params.get('q')
    if return_json:
        return execute_xpath(xpath_string, 'xpath', uuid, version)
    else:
        return xpath_book_html(request, uuid, version)


def xpath_page(request, uuid, version):
    """Given a page UUID (and optional version), returns a JSON object of
    results, as in xpath_book()"""
    xpath_string = request.params.get('q')
    return execute_xpath(xpath_string, 'xpath-module', uuid, version)


def _get_content_json_xpath(request, uuid, version):
    """Return a content as a dict from its ident-hash (uuid@version)."""

    settings = get_current_registry().settings
    as_collated = asbool(request.GET.get('as_collated', True))
    ident_hash = join_ident_hash(uuid, version)
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            result = get_content_metadata(uuid, version, cursor)
            # Grab the collection tree.
            result['tree'] = get_tree(ident_hash, cursor,
                                      as_collated=as_collated)
            result['collated'] = as_collated
            if not result['tree']:
                # If collated tree is not available, get the uncollated
                # tree.
                result['tree'] = get_tree(ident_hash, cursor)
                result['collated'] = False

    return result


def xpath_book_html(request, uuid, version):
    """Build the HTML tree."""
    result = _get_content_json_xpath(request, uuid, version)

    content = tree_to_html_xpath(result['tree'])

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = 'application/xhtml+xml'
    resp.body = content
    return resp


def tree_to_html_xpath(tree):
    """Return html list version of book tree."""
    ul = etree.Element('ul')
    html_listify_xpath([tree], ul)
    return HTML_WRAPPER.format(etree.tostring(ul))


def html_listify_xpath(tree, root_ul_element, parent_id=None):
    """Recursively construct HTML nested list version of book tree, adding
    hrefs to the page titles which are links to the the API endpoint which runs
    the xpath on that page CNXML. The original caller should not call this
    function with the `parent_id` defined.

    """
    request = get_current_request()
    querystring = "&q=" + request.params.get('q', '')
    is_first_node = parent_id is None
    if is_first_node:
        parent_id = tree[0]['id']
    for node in tree:
        li_elm = etree.SubElement(root_ul_element, 'li')
        a_elm = etree.SubElement(li_elm, 'a')
        a_elm.text = node['title']
        if node['id'] != 'subcol':
            if is_first_node:
                a_elm.set('href', request.route_path('xpath') +
                          '?id=' + node['id'] + querystring)
            else:
                a_elm.set('href', request.route_path('xpath') +
                          '?id=' + node['id'] + querystring)
        if 'contents' in node:
            elm = etree.SubElement(li_elm, 'ul')
            html_listify_xpath(node['contents'], elm, parent_id)


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
            return results
    else:
        results = {'results': list(xpath_page(request, uuid, version))}
        resp.body = json.dumps(results)
        resp.content_type = 'application/json'

    resp.status = "200 OK"
    return resp
