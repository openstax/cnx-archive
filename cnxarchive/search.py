# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database search utilties."""
import os
import re
from collections import Mapping, OrderedDict, Sequence
from datetime import datetime
from time import strptime

from cnxquerygrammar.query_parser import grammar, DictFormater
from parsimonious.exceptions import IncompleteParseError
from psycopg2.tz import FixedOffsetTimezone, LocalTimezone

from .database import SQL_DIRECTORY, db_connect
from .utils import (
    portaltype_to_mimetype, COLLECTION_MIMETYPE, MODULE_MIMETYPE,
    PORTALTYPE_TO_MIMETYPE_MAPPING, utf8
    )
import logging

logger = logging.getLogger('cnxarchive')


__all__ = ('search', 'Query',)


here = os.path.abspath(os.path.dirname(__file__))
LOCAL_TZINFO = LocalTimezone()
with open(os.path.join(here, 'data', 'common-english-words.txt'), 'r') as f:
    # stopwords are all the common english words plus single characters
    STOPWORDS = (f.read().split(',') +
                 [chr(i) for i in range(ord('a'), ord('z') + 1)])
# WILDCARD_KEYWORD = 'text'
# VALID_FILTER_KEYWORDS = ('type', 'pubYear', 'authorID', 'keyword', 'subject',
#                          'language', 'title', 'author', 'abstract')
# The maximum number of keywords and authors to return in the search result
# counts
MAX_VALUES_FOR_KEYWORDS = 100
MAX_VALUES_FOR_AUTHORS = 100
SORT_VALUES_MAPPING = {
    'pubdate': 'revised DESC',
    'version': 'version DESC',
    'popularity': 'rank DESC NULLS LAST',
    }
DEFAULT_SEARCH_WEIGHTS = OrderedDict([
    ])
SQL_SEARCH_DIRECTORY = os.path.join(SQL_DIRECTORY, 'search')


def _read_sql_file(name, root=SQL_SEARCH_DIRECTORY, extension='.sql',
                   remove_comments=False):
    path = os.path.join(root, '{}{}'.format(name, extension))
    with open(path, 'r') as fp:
        if remove_comments:
            file = '\n'.join([l for l in fp if not l.startswith('--')])
        else:
            file = fp.read()
    return file


SQL_SEARCH_TEMPLATES = {name: _read_sql_file(name, extension='.part.sql',
                                             remove_comments=True)
                        for name in DEFAULT_SEARCH_WEIGHTS.keys()}
SQL_WEIGHTED_SELECT_WRAPPER = _read_sql_file('wrapper')
SQL_QUICK_SELECT_WRAPPER = _read_sql_file('quick-wrapper')
SEARCH_QUERY = _read_sql_file('query')
QUERY_FIELD_ITEM_SEPARATOR = ';--;'
QUERY_FIELD_PAIR_SEPARATOR = '-::-'

SET_OPERATORS = ('OR', 'AND', 'NOT',)
QUERY_TYPES = ('OR', 'AND', 'weakAND',)
DEFAULT_QUERY_TYPE = QUERY_TYPES[-1]

DEFAULT_PER_PAGE = 20


class Query(Sequence):
    """A structured respresentation of the query string."""

    def __init__(self, query):
        """Create a query object."""
        self.filters = [q for q in query if q[0] not in ('text', 'sort')]
        self.sorts = [q[1] for q in query if q[0] == 'sort']
        self.terms = [q for q in query
                      if q not in self.filters and q[0] != 'sort']

    def __repr__(self):
        """String repr."""
        s = "<{} with '{}' >".format(self.__class__.__name__, self.terms)
        return s

    def __getitem__(self, index):
        """Return terms."""
        return self.terms[index]

    def __len__(self):
        """Length is number of terms."""
        return len(self.terms)

    @classmethod
    def fix_quotes(cls, query_string):
        """Heuristic attempt to fix unbalanced quotes in query_string."""
        if query_string.count('"') % 2 == 0:
            # no unbalanced quotes to fix
            return query_string

        fields = []  # contains what's matched by the regexp
        # e.g. fields = ['sort:pubDate', 'author:"first last"']

        def f(match):
            fields.append(match.string[match.start():match.end()])
            return ''

        # terms will be all the search terms that don't have a field
        terms = re.sub(r'[^\s:]*:("[^"]*"|[^\s]*)', f, query_string)
        query_string = '{}" {}'.format(terms.strip(), ' '.join(fields))
        return query_string

    @classmethod
    def from_raw_query(cls, query_string):
        """Parse raw string to query.

        Given a raw string (typically typed by the user),
        parse to a structured format and initialize the class.
        """
        try:
            node_tree = grammar.parse(query_string)
        except IncompleteParseError:
            query_string = cls.fix_quotes(query_string)
            node_tree = grammar.parse(query_string)

        structured_query = DictFormater().visit(node_tree)

        return cls([t for t in structured_query
                    if t[1].lower() not in STOPWORDS])


class QueryRecord(Mapping):
    """A query record wrapper to parse hit values and add behavior."""

    def __init__(self, **kwargs):
        self._record = {k: v for k, v in kwargs.items()
                        if k not in ('_keys', 'matched', 'fields',)}
        if self._record.get('mediaType') in PORTALTYPE_TO_MIMETYPE_MAPPING:
            self._record['mediaType'] = \
                portaltype_to_mimetype(self._record['mediaType'])
        self.matched = {}
        self.fields = {}
        # Parse the matching fields
        for field_record in kwargs['_keys'].split(QUERY_FIELD_ITEM_SEPARATOR):

            if len(field_record) > 0:
                term, key = field_record.split(QUERY_FIELD_PAIR_SEPARATOR)
                self.matched.setdefault(term, set()).add(key)
                self.fields.setdefault(key, set()).add(term)
        self.match_hits = (self.matched, self.fields)

    def __repr__(self):
        s = "<{} id='{}'>".format(self.__class__.__name__, self['id'])
        return s

    def __getitem__(self, key):
        return self._record[key]

    def __iter__(self):
        return iter(self._record)

    def __len__(self):
        return len(self._record)

    @property
    def highlighted_abstract(self):
        """Highlight the found terms in the abstract text."""
        abstract_terms = self.fields.get('abstract', [])
        if abstract_terms:
            sql = _read_sql_file('highlighted-abstract')
        else:
            sql = _read_sql_file('get-abstract')
        arguments = {'id': self['id'],
                     'query': ' & '.join(abstract_terms),
                     }
        with db_connect() as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(sql, arguments)
                hl_abstract = cursor.fetchone()
        if hl_abstract:
            return hl_abstract[0]

    @property
    def highlighted_fulltext(self):
        """Highlight the found terms in the fulltext."""
        terms = self.fields.get('fulltext', [])
        if not terms:
            return None
        arguments = {'id': self['id'],
                     'query': ' & '.join(terms),
                     }
        with db_connect() as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(_read_sql_file('highlighted-fulltext'),
                               arguments)
                hl_fulltext = cursor.fetchone()[0]
        return hl_fulltext


class QueryResults(Sequence):
    """List of search results.

    A listing of query results as well as hit counts and the parsed query
    string. The query is necessary to do in-python set operations on the
    rows.
    """

    def __init__(self, rows, query, query_type=DEFAULT_QUERY_TYPE):
        if query_type not in QUERY_TYPES:
            raise ValueError("Invalid query type supplied: '{}'"
                             .format(query_type))
        self._query = query
        self._records = [QueryRecord(**r[0]) for r in rows]
        self.counts = {
            'type': self._count_media(),
            'subject': self._count_field('subjects'),
            'keyword': self._count_field('keywords',
                                         max_results=MAX_VALUES_FOR_KEYWORDS),
            'authorID': self._count_authors(
                max_results=MAX_VALUES_FOR_AUTHORS),
            'pubYear': self._count_publication_year(),
            }

    def __repr__(self):
        s = "<{} with '{}' results>".format(self.__class__.__name__,
                                            len(self))
        return s

    def __getitem__(self, index):
        return self._records[index]

    def __len__(self):
        return len(self._records)

    @property
    def auxiliary(self):
        return {'authors': self._auxiliary_authors,
                'types': self._auxiliary_types,
                }

    @property
    def _auxiliary_authors(self):
        attr_name = '_aux_authors'
        if hasattr(self, attr_name):
            return getattr(self, attr_name)

        # Used to make the dict hashable for a set([]).
        class hashabledict(dict):
            def __hash__(self):
                # Use the unique value 'id' as the hash value.
                return hash(self['id'])

        authors = set([])
        for rec in self._records:
            for author in rec['authors']:
                # The author is in dict format, just use it.
                authors.add(hashabledict(author))

        authors = list(authors)
        authors.sort(lambda x, y: cmp(y['id'], x['id']))
        setattr(self, attr_name, authors)
        return getattr(self, attr_name)

    @property
    def _auxiliary_types(self):
        # If we ever add types beyond book and page,
        #   we'll want to change this.
        return [{'id': COLLECTION_MIMETYPE, 'name': 'Book'},
                {'id': MODULE_MIMETYPE, 'name': 'Page'}]

    def _count_field(self, field_name, sorted=True, max_results=None):
        counts = {}
        for rec in self._records:
            for value in rec[field_name]:
                counts.setdefault(value, 0)
                counts[value] += 1

        if max_results:
            # limit the number of results we return
            counts = counts.items()
            # sort counts by the count with highest count first
            counts.sort(lambda a, b: cmp(a[1], b[1]), reverse=True)
            counts = counts[:max_results]

        if sorted:
            if isinstance(counts, dict):
                counts = counts.items()
            # Sort counts by the name alphabetically
            counts.sort(lambda a, b: cmp(a[0].lower(), b[0].lower()))
        else:
            counts = counts.iteritems()

        return counts

    def _count_media(self):
        counts = {
            MODULE_MIMETYPE: 0,
            COLLECTION_MIMETYPE: 0,
            }
        for rec in self._records:
            counts[rec['mediaType']] += 1
        return [(COLLECTION_MIMETYPE, counts[COLLECTION_MIMETYPE],),
                (MODULE_MIMETYPE, counts[MODULE_MIMETYPE],),
                ]

    def _count_authors(self, max_results=None):
        counts = {}
        uid_author = {}  # look up author record by uid
        for rec in self._records:
            for author in rec['authors']:
                uid = author['id']
                counts.setdefault(uid, 0)
                counts[uid] += 1
                uid_author.setdefault(uid, author)
        authors = []
        for uid, count in counts.iteritems():
            author = uid_author[uid]
            authors.append(((uid, author,), count))

        if max_results:
            # limit the number of results we return
            # sort counts by the count with highest count first
            authors.sort(lambda a, b: cmp(a[1], b[1]), reverse=True)
            authors = authors[:max_results]

        def sort_name(a, b):
            (uid_a, author_a), count_a = a
            (uid_b, author_b), count_b = b
            result = cmp(author_a['surname'], author_b['surname'])
            if result == 0:
                result = cmp(author_a['firstname'], author_b['firstname'])
            return result
        # Sort authors by surname then first name
        authors.sort(sort_name)
        authors = [(a[0][0], a[1],) for a in authors]
        return authors

    def _count_publication_year(self):
        counts = {}
        for rec in self._records:
            date = rec['pubDate']
            if date is None:
                continue
            date = datetime(*strptime(date, "%Y-%m-%dT%H:%M:%SZ")[:6],
                            tzinfo=FixedOffsetTimezone())
            year = unicode(date.astimezone(LOCAL_TZINFO).year)
            counts.setdefault(year, 0)
            counts[year] += 1
        counts = counts.items()
        # Sort pubYear in reverse chronological order
        counts.sort(lambda a, b: cmp(a[0], b[0]), reverse=True)
        return counts


def _transmute_sort(sort_value):
    """Provide a value translation to the SQL column name."""
    try:
        return SORT_VALUES_MAPPING[sort_value.lower()]
    except KeyError:
        raise ValueError("Invalid sort key '{}' provided.".format(sort_value))


def _convert(tup, dictlist):
    """
    :param tup: a list of tuples
    :param di: a dictionary converted from tup
    :return: dictionary
    """
    di = {}
    for a, b in tup:
        di.setdefault(a, []).append(b)
    for key, val in di.items():
        dictlist.append((key, val))
    return dictlist


def _upper(val_list):
    """
    :param val_list: a list of strings
    :return: a list of upper-cased strings
    """
    res = []
    for ele in val_list:
        res.append(ele.upper())
    return res


def _filter_stop_words(raw_query):
    return [term for term in raw_query if term.lower() not in STOPWORDS]


def _build_search(structured_query):
    """Construct search statment for db execution.

    Produces the search statement and argument dictionary to be executed
    by the DBAPI v2 execute method.
    For example, ``cursor.execute(*_build_search(query, weights))``

    :param query: containing terms, filters, and sorts.
    :type query: Query
    :param weights: weight values to assign to each keyword search field
    :type weights: dictionary of field names to weight integers
    :returns: the build statement and the arguments used against it
    :rtype: a two value tuple of a SQL template and a dictionary of
            arguments to pass into that template
    """
    arguments = {}

    # get text terms and filter out common words
    text_terms = [term for ttype, term in structured_query.terms
                  if ttype == 'text']

    text_terms_wo_stopwords = [term for term in text_terms
                               if term.lower() not in STOPWORDS]
    # sql where clauses
    conditions = {'text_terms': '', 'pubYear': '', 'authorID': '', 'type': '',
                  'keyword': '', 'subject': '', 'language': '', 'title': '',
                  'author': '', 'abstract': ''}

    # if there are other search terms (not type "text") or if the text
    # terms do not only consist of stopwords, then use the text terms
    # without stopwords
    if arguments or text_terms_wo_stopwords:
        text_terms = text_terms_wo_stopwords
    arguments.update({'text_terms': ' '.join(text_terms)})
    # raise Exception(structured_query.filters, structured_query.terms)

    if len(text_terms) > 0:
        conditions['text_terms'] = 'AND module_idx \
                                    @@ plainto_tsquery(%(text_terms)s)'

    # build fulltext keys
    fulltext_key = []
    for term in text_terms_wo_stopwords:
        fulltext_key.append(term + '-::-fulltext')
    arguments.update({'fulltext_key':  ';--;'.join(fulltext_key)})

    idx = 0
    invalid_filters = []
    filters = _convert(structured_query.filters, [])

    while idx < len(filters):
        keyword = filters[idx][0]
        value = filters[idx][1]
        if keyword == 'pubYear':
            conditions['pubYear'] = 'AND extract(year from cm.revised) = \
                                     %(pubYear)s'
            arguments.update({'pubYear': value[0]})
        elif keyword == 'authorID':
            conditions['authorID'] = 'AND ARRAY[%(authorID)s] \
                                      <@ cm.authors'
            arguments.update({'authorID': value[0]})
        elif keyword == 'type':
            value[0] = value[0].lower()

            conditions['type'] = 'AND cm.portal_type = %(type)s'
            if value[0] != 'book' and value[0] != 'collection' and \
                    value[0] != 'page' and value[0] != 'module':
                invalid_filters.append(idx)
            value[0] = 'Collection' if (value[0] == 'book' or
                                        value[0] == 'collection') else 'Module'
            arguments.update({'type': value[0]})
        elif keyword == 'keyword':
            value = _upper(value)
            conditions['keyword'] = 'AND cm.module_ident = \
                                     ANY(WITH target AS ( \
                                     SELECT lm.module_ident AS id, \
                                     array_agg(UPPER(kw.word)) AS akw \
                                     FROM latest_modules lm, \
                                     modulekeywords mk, \
                                     keywords kw \
                                     WHERE lm.module_ident = mk.module_ident \
                                     AND kw.keywordid = mk.keywordid \
                                     GROUP BY id) \
                                     SELECT target.id FROM target WHERE \
                                     target.akw @> %(keyword)s)'
            arguments.update({'keyword': value})
        elif keyword == 'subject':
            conditions['subject'] = 'AND cm.module_ident = \
                                     ANY(WITH sub AS ( \
                                     SELECT module_ident AS id, \
                                     array_agg(tag) AS atag \
                                     FROM latest_modules \
                                     NATURAL JOIN \
                                     moduletags NATURAL JOIN \
                                     tags GROUP BY id) \
                                     SELECT sub.id FROM sub WHERE \
                                     sub.atag @> %(subject)s)'
            arguments.update({'subject': value})
        elif keyword == 'language':
            conditions['language'] = 'AND cm.language = %(language)s'
            arguments.update({'language': value[0]})
        elif keyword == 'title':
            conditions['title'] = 'AND strip_html(cm.name) ~* \
                                   %(title)s'
            arguments.update({'title': value[0]})
        elif keyword == 'author':
            conditions['author'] = 'AND cm.module_ident = \
                                    ANY(WITH name AS ( \
                                    SELECT username FROM users u WHERE \
                                    u.first_name||\' \'||u.last_name \
                                    ~* %(author)s) \
                                    SELECT lm.module_ident \
                                    FROM latest_modules lm \
                                    JOIN name n ON ARRAY[n.username] \
                                    <@ lm.authors)'
            arguments.update({'author': value[0]})
        elif keyword == 'abstract':
            conditions['abstract'] = 'AND cm.module_ident = \
                                      ANY(SELECT lm.module_ident FROM \
                                      latest_modules lm, \
                                      abstracts ab WHERE\
                                      lm.abstractid = ab.abstractid \
                                      AND ab.abstract \
                                      ~* %(abstract)s)'
            arguments.update({'abstract': value[0]})
        else:
            # Invalid filter!
            invalid_filters.append(idx)
        idx += 1

    if len(invalid_filters) == len(structured_query.filters) and \
            len(structured_query.terms) == 0:
        # Either query terms are all invalid filters
        # or we received a null query.
        # Clear the filter list in this case.
        structured_query.filters = []
        return None, None

    for invalid_filter_idx in invalid_filters:
        # Remove invalid filters.
        del structured_query.filters[invalid_filter_idx]

    # Add the arguments for sorting.
    sorts = ['portal_type']
    if structured_query.sorts:
        for sort in structured_query.sorts:
            # These sort values are not the name of the column used
            #   in the database.
            stmt = _transmute_sort(sort)
            sorts.append(stmt)
    sorts.extend(('weight DESC', 'uuid DESC',))
    sorts = ', '.join(sorts)

    statement = SQL_QUICK_SELECT_WRAPPER.format(conditions['pubYear'],
                                                conditions['authorID'],
                                                conditions['type'],
                                                conditions['keyword'],
                                                conditions['subject'],
                                                conditions['text_terms'],
                                                conditions['language'],
                                                conditions['title'],
                                                conditions['author'],
                                                conditions['abstract'],
                                                sorts=sorts)
    return statement, arguments


def search(query, query_type=DEFAULT_QUERY_TYPE):
    """Search database using parsed query.

    Executes a database search query from the given ``query``
    (a ``Query`` object) and optionally accepts a list of search weights.
    By default, the search results are ordered by weight.

    :param query: containing terms, filters, and sorts.
    :type query: Query
    :returns: a sequence of records that match the query conditions
    :rtype: QueryResults (which is a sequence of QueryRecord objects)
    """

    # Build the SQL statement.
    statement, arguments = _build_search(query)

    # Execute the SQL.
    if statement is None and arguments is None:
        return QueryResults([], [], 'AND')
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(statement, arguments)
            search_results = cursor.fetchall()
    # Wrap the SQL results.
    return QueryResults(search_results, query, query_type)
