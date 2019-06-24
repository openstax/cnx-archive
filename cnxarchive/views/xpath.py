import json
import re
from urllib import urlencode
from functools import partial, wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from pyramid import httpexceptions
from pyramid.view import view_config

from ..database import SQL, db_connect
from ..utils import (
    IdentHashShortId, IdentHashMissingVersion, IdentHashSyntaxError,
    split_ident_hash, COLLECTION_MIMETYPE, join_ident_hash
)
from .helpers import get_uuid, get_latest_version


# XXX for development
SQL['contextual-uuid-to-key-data-lookup'] = """\
WITH RECURSIVE t(node, title, path, value, is_collated) AS (
    SELECT
      nodeid,
      title,
      ARRAY [nodeid],
      documentid,
      is_collated
    FROM trees AS tr, modules AS m
    WHERE ident_hash(m.uuid, m.major_version, m.minor_version) = %(ident_hash)s
     AND tr.documentid = m.module_ident
     AND tr.is_collated = %(is_collated)s

  UNION ALL

    SELECT c1.nodeid, c1.title, t.path || ARRAY [c1.nodeid], c1.documentid, c1.is_collated /* Recursion */
    FROM trees AS c1
    JOIN t ON (c1.parent_id = t.node)
    WHERE NOT nodeid = ANY (t.path) AND t.is_collated = c1.is_collated
)
SELECT DISTINCT
  m.module_ident as module_ident,
  m.portal_type as portal_type,
  coalesce(t.title, m.name) AS name,
  m.uuid AS uuid,
  m.major_version AS major_version,
  m.minor_version AS minor_version
FROM t JOIN modules m ON t.value = m.module_ident;
"""
SQL['get-core-info'] = """\
SELECT 	module_ident, portal_type, name, uuid, major_version, minor_version
FROM modules
WHERE ident_hash(uuid, major_version, minor_version) = %(ident_hash)s;
"""
SQL['query-module_files-by-xpath'] = """\
SELECT module_ident, array_agg(matches)
FROM (
SELECT
  module_ident,
  unnest(xpath(e%(xpath)s, CAST(convert_from(file, 'UTF-8') AS XML),
              ARRAY[ARRAY['cnx', 'http://cnx.rice.edu/cnxml'],
                    ARRAY['c', 'http://cnx.rice.edu/cnxml'],
                    ARRAY['system', 'http://cnx.rice.edu/system-info'],
                    ARRAY['math', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['mml', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['m', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['md', 'http://cnx.rice.edu/mdml'],
                    ARRAY['qml', 'http://cnx.rice.edu/qml/1.0'],
                    ARRAY['bib', 'http://bibtexml.sf.net/'],
                    ARRAY['xhtml', 'http://www.w3.org/1999/xhtml'],
                    ARRAY['h', 'http://www.w3.org/1999/xhtml'],
                    ARRAY['data', 'http://www.w3.org/TR/html5/dom.html#custom-data-attribute'],
                    ARRAY['cmlnle', 'http://katalysteducation.org/cmlnle/1.0']]
        ))::TEXT AS matches
FROM modules AS m
NATURAL JOIN module_files
NATURAL JOIN files
WHERE m.module_ident = any(%(idents)s)
AND filename = %(filename)s
) AS results
GROUP BY module_ident
"""
SQL['query-collated_file_associations-by-xpath'] = """\
SELECT item, array_agg(matches)
FROM (
SELECT
  item,
  unnest(xpath(e%(xpath)s, CAST(convert_from(file, 'UTF-8') AS XML),
              ARRAY[ARRAY['cnx', 'http://cnx.rice.edu/cnxml'],
                    ARRAY['c', 'http://cnx.rice.edu/cnxml'],
                    ARRAY['system', 'http://cnx.rice.edu/system-info'],
                    ARRAY['math', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['mml', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['m', 'http://www.w3.org/1998/Math/MathML'],
                    ARRAY['md', 'http://cnx.rice.edu/mdml'],
                    ARRAY['qml', 'http://cnx.rice.edu/qml/1.0'],
                    ARRAY['bib', 'http://bibtexml.sf.net/'],
                    ARRAY['xhtml', 'http://www.w3.org/1999/xhtml'],
                    ARRAY['h', 'http://www.w3.org/1999/xhtml'],
                    ARRAY['data', 'http://www.w3.org/TR/html5/dom.html#custom-data-attribute'],
                    ARRAY['cmlnle', 'http://katalysteducation.org/cmlnle/1.0']]
        ))::TEXT AS matches
FROM collated_file_associations AS cfa
NATURAL JOIN files
WHERE cfa.item = any(%(idents)s)
AND cfa.context = %(context)s -- book context
) AS results
GROUP BY item;
"""

# These represent the acceptable document types the xpath search can query
DOC_TYPES = (
    'cnxml',
    'html',
    'baked-html',
)
DEFAULT_DOC_TYPE = DOC_TYPES[0]

# XXX Can't these be imported from somewhere?
NAMESPACES = {
    'cnx': 'http://cnx.rice.edu/cnxml',
    'c': 'http://cnx.rice.edu/cnxml',
    'system': 'http://cnx.rice.edu/system-info',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'mml': 'http://www.w3.org/1998/Math/MathML',
    'm': 'http://www.w3.org/1998/Math/MathML',
    'md': 'http://cnx.rice.edu/mdml',
    'qml': 'http://cnx.rice.edu/qml/1.0',
    'bib': 'http://bibtexml.sf.net/',
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'h': 'http://www.w3.org/1999/xhtml',
    'data': 'http://www.w3.org/TR/html5/dom.html#custom-data-attribute',
    'cmlnle': 'http://katalysteducation.org/cmlnle/1.0',
}


def lookup_documents_to_query(ident_hash, as_collated=False):
    """Looks up key information about documents to query including:
    title, uuid, version and module_ident.
    A list of documents will be returned, for a book this will be
    a list of documents in that book. For a page it will be a list
    containing only that page.

    """
    params = {
        'ident_hash': ident_hash,
        'is_collated': as_collated,
    }
    with db_connect() as db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Lookup base information about the module
            cursor.execute(SQL['get-core-info'], params)
            row = cursor.fetchone()

            type_ = row['portal_type']

            if 'Composite' in type_:
                raise TypeError("Can't process composite content")
            elif type_ == 'Module':
                results = [dict(row.items())]
            else:
                cursor.execute(SQL['contextual-uuid-to-key-data-lookup'], params)
                results = [dict(row.items()) for row in cursor]

    return results


def _xpath_query(docs, xpath, extension):
    """\
    Does a `xpath` query on the database for the given `docs` against
    the content files. The given `docs` is a sequence of integers representing
    `module_ident`s of the content to query.

    The type of content file to query is specified by extentions.

    """
    params = {
        'filename': 'index{}'.format(extension),
        'idents': list(docs),
        'xpath': xpath,
    }
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(SQL['query-module_files-by-xpath'], params)
            return cursor.fetchall()


def _collated_xpath_query(docs, xpath, context):
    """\
    Does a `xpath` query on the database for the given `docs` against
    the content files. The given `docs` is a sequence of integers representing
    `module_ident`s of the content to query.

    The type of content file to query is specified by extentions.

    """
    params = {
        'context': context,
        'idents': list(docs),
        'xpath': xpath,
    }
    with db_connect() as db_conn:
        with db_conn.cursor() as cursor:
            sql = SQL['query-collated_file_associations-by-xpath']
            cursor.execute(sql, params)
            return cursor.fetchall()


def query_documents_by_xpath(docs, xpath, type_=DEFAULT_DOC_TYPE,
                             context_doc=None):
    """\
    Query the given set of `docs` using the given `xpath` within by the
    requested `type_`.

    `docs` is a sequence of module_ident values.
    `xpath` is a string containing the xpath query
    `type_` is the type of content to query (i.e. cnxml, html, baked-html)

    """
    if type_ not in DOC_TYPES:
        raise TypeError('Invalid document type specified: {}'.format(type_))
    elif type_ == DOC_TYPES[2] and context_doc is None:
        raise ValueError('Cannot query a book without the book context')

    querier = {
        # cnxml
        DOC_TYPES[0]: partial(_xpath_query, extension='.cnxml'),
        # html
        DOC_TYPES[1]: partial(_xpath_query, extension='.cnxml.html'),
        # baked-html
        DOC_TYPES[2]: partial(_collated_xpath_query, context=context_doc),
    }[type_]  # psuedo-switch-statement
    return querier(docs, xpath)


class XPathView(object):

    def __init__(self, request):
        self.request = request
        self.extract_params()

    def extract_params(self):
        id = self.request.params.get('id')
        q = self.request.params.get('q')

        if not id or not q:
            raise httpexceptions.HTTPBadRequest(
                'You must supply both a UUID and an XPath'
            )

        # FIXME This looks like a copy&paste that should be refactored
        #       to a single function that gets us the correct info.
        try:
            uuid, version = split_ident_hash(id)
        except IdentHashShortId as e:
            uuid = get_uuid(e.id)
            version = e.version
        except IdentHashMissingVersion as e:
            uuid = e.id
            version = get_latest_version(e.id)
        except IdentHashSyntaxError:
            raise httpexceptions.HTTPBadRequest('invalid id supplied')
        ident_hash = join_ident_hash(uuid, version)

        self.ident_hash = ident_hash
        self.xpath_query = q

    @property
    def match_data(self):
        # Lookup documents to query
        docs = lookup_documents_to_query(self.ident_hash)

        # Query Documents
        docs_map = dict([(x['module_ident'], x,) for x in docs])
        query_results = query_documents_by_xpath(docs_map.keys(), self.xpath_query)

        # Combined the query results with the mapping
        for ident, matches in query_results:
            docs_map[ident]['matches'] = matches
            docs_map[ident]['ident_hash'] = join_ident_hash(
                docs_map[ident]['uuid'],
                (docs_map[ident]['major_version'],
                 docs_map[ident]['minor_version'],
                ),
            )
            docs_map[ident]['uri'] = self.request.route_path(
                'content',
                ident_hash=docs_map[ident]['ident_hash'],
            )
            del docs_map[ident]['module_ident']

        return list([x for x in docs_map.values() if 'matches' in x])

    @view_config(route_name='xpath-json', request_method='GET',
                 renderer='json',
                 http_cache=(60, {'public': True}))
    def json(self):
        """Produces the data used to render the HTML view"""
        return self.match_data

    @view_config(route_name='xpath', request_method='GET',
                 renderer='templates/xpath.html',
                 http_cache=(60, {'public': True}))
    def html(self):
        """Produces the data used to render the HTML view"""
        return {
            'identifier': self.ident_hash,
            'uri': self.request.route_path('content', self.ident_hash),
            'query': self.xpath_query,
            'request': self.request,
            'results': self.match_data,
        }
