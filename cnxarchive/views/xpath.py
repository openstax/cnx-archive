# -*- coding: utf-8 -*-
from functools import partial, wraps

from psycopg2.extras import RealDictCursor
from pyramid import httpexceptions
from pyramid.view import view_config

from ..database import SQL, db_connect
from ..utils import (
    IdentHashSyntaxError,
    join_ident_hash,
    magically_split_ident_hash,
)


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

            type_ = row['type']

            if 'Module' in type_:
                results = [dict(row.items())]
            else:
                cursor.execute(
                    SQL['get-book-core-info'],
                    params,
                )
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
        doc_type = self.request.params.get('type', DEFAULT_DOC_TYPE)

        if doc_type not in DOC_TYPES:
            raise httpexceptions.HTTPBadRequest('Invalid `type` specified')

        if not id or not q:
            raise httpexceptions.HTTPBadRequest(
                'You must supply both a UUID and an XPath'
            )

        try:
            book_context, page_context = magically_split_ident_hash(id)
        except IdentHashSyntaxError:
            raise httpexceptions.HTTPBadRequest('invalid id supplied')
        self.ident_hash = join_ident_hash(*page_context)

        if book_context:
            self.book_context = join_ident_hash(*book_context)
        else:
            self.book_context = None
        self.xpath_query = q
        self.doc_type = doc_type

    def find_book_context_ident(self, contextual_doc):
        """Given the request's knowledge and information about the
        contextual document (given as `contextual_doc`), this attempts to
        find the book's ident if the search needs it. The book context
        is required when searching for 'baked-html'
        (the value of `doc_type`), because the data is stored in relation
        to the book.

        """
        is_baked_html_book_search = (
            self.doc_type == DOC_TYPES[2] and
            contextual_doc['type'] == 'Collection'
        )
        is_baked_html_page_without_book_context_search = (
            self.doc_type == DOC_TYPES[2] and
            self.book_context is None
        )
        is_baked_html_page_with_book_context_search = (
            self.doc_type == DOC_TYPES[2] and
            self.book_context is not None
        )

        if is_baked_html_book_search:
            # If requesting to search baked-html without the book context,
            # the context is therefore a book itself.
            context = contextual_doc['module_ident']
        elif is_baked_html_page_without_book_context_search:
            # If requesting to search baked-html without a book context.
            raise httpexceptions.HTTPBadRequest(
                "searching by 'baked-html' without the `id` within a book "
                "context is invalid. Use `{book-id}:{page-id}` for "
                "the `id` parameter."
            )
        elif is_baked_html_page_with_book_context_search:
            context = [
                doc
                for doc in lookup_documents_to_query(
                    self.book_context,
                    as_collated=(self.doc_type == DOC_TYPES[2]),
                )
                if doc['ident_hash'] == self.book_context
            ][0]['module_ident']
        else:
            context = None
        return context

    @property
    def match_data(self):
        # Lookup documents to query
        docs = lookup_documents_to_query(
            self.ident_hash,
            as_collated=(self.doc_type == DOC_TYPES[2]),
        )

        # Assemble the data for results and intermediary use
        docs_map = dict([(x['module_ident'], x,) for x in docs])

        # Find the context ... aka page within a book
        contextual_doc = [
            doc for doc in docs
            if join_ident_hash(doc['uuid'], doc['version']) == self.ident_hash
        ][0]
        book_context_ident = self.find_book_context_ident(contextual_doc)

        # Query Documents
        query_results = query_documents_by_xpath(
            docs_map.keys(),
            self.xpath_query,
            self.doc_type,
            book_context_ident,
        )

        # Combined the query results with the mapping
        for ident, matches in query_results:
            docs_map[ident]['matches'] = [x.decode('utf-8') for x in matches]
            docs_map[ident]['uri'] = self.request.route_path(
                'content',
                ident_hash=docs_map[ident]['ident_hash'],
            )
            docs_map[ident]['title'] = docs_map[ident]['title'].decode('utf-8')
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
