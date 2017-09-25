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
from pyramid.threadlocal import get_current_registry

from . import config
from .database import SQL_DIRECTORY, db_connect
from .utils import (
    portaltype_to_mimetype, COLLECTION_MIMETYPE, MODULE_MIMETYPE,
    PORTALTYPE_TO_MIMETYPE_MAPPING, utf8
    )


__all__ = ('search', 'Query',)


here = os.path.abspath(os.path.dirname(__file__))
LOCAL_TZINFO = LocalTimezone()
with open(os.path.join(here, 'data', 'common-english-words.txt'), 'r') as f:
    # stopwords are all the common english words plus single characters
    STOPWORDS = (f.read().split(',') +
                 [chr(i) for i in range(ord('a'), ord('z') + 1)])
WILDCARD_KEYWORD = 'text'
VALID_FILTER_KEYWORDS = ('type', 'pubYear', 'authorID', 'submitterID')
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
    ('parentauthor', 0),
    ('language', 5),
    ('subject', 10),
    ('fulltext', 1),
    ('abstract', 1),
    ('keyword', 10),
    ('author', 50),
    ('editor', 20),
    ('translator', 40),
    ('maintainer', 10),
    ('licensor', 10),
    ('exact_title', 100),
    ('title', 10),
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
        self.filters = [q for q in query if q[0] in VALID_FILTER_KEYWORDS]
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


def _apply_query_type(records, query, query_type):
    """Boolean combination of records.

    Apply a AND, weak AND or OR operation to the results records.
    Returns the revised list of records, unmatched terms, and matched terms.
    """
    # These all get revised an returned at the end.
    query = list(set(query))  # Ensure a unique query list
    matched_terms = []
    unmatched_terms = query
    revised_records = records

    if records and query:  # no query implies limit-only case
        #: List of records that match all terms.
        all_matched_records = []
        term_matches = []
        query_terms_wo_stopwords = [utf8(term) for ttype, term in query
                                    if ttype != 'text' or term.lower()
                                    not in STOPWORDS]
        if not query_terms_wo_stopwords:
            query_terms_wo_stopwords = [utf8(term) for ttype, term in query]
        query_terms_wo_stopwords.sort()
        for rec in records:
            if sorted(rec.matched.keys()) == query_terms_wo_stopwords:
                all_matched_records.append(rec)
            term_matches.extend(utf8(list(rec.matched)))

        unmatched_terms = [term for term in query
                           if utf8(term[1]) not in term_matches]
        if unmatched_terms:
            matching_length = len(query) - len(unmatched_terms)
            #: List of records that match some of the terms.
            some_matched_records = [rec for rec in records
                                    if len(rec.matched) == matching_length]
            matched_terms = [term for term in query
                             if utf8(term[1]) in term_matches]
        else:
            some_matched_records = all_matched_records
            matched_terms = query

        if query_type.upper() == 'AND':
            revised_records = all_matched_records
        elif query_type.upper() == 'WEAKAND':
            revised_records = some_matched_records
        # elif query_type.upper() == 'OR':
        #     pass
    return revised_records, unmatched_terms, matched_terms


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
        # Capture all the rows for interal usage.
        self._all_records = [QueryRecord(**r[0]) for r in rows]
        # Apply the query type to the results.
        applied_results = _apply_query_type(self._all_records, self._query,
                                            query_type)
        self._records = applied_results[0]
        self._unmatched_terms = applied_results[1]
        self._matched_terms = applied_results[2]
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


def _transmute_filter(keyword, value):
    """SQL producer for conditionals.

    Produces a SQL condition statement that is a python format statement,
    to be used with the string ``format`` method.
    This is to allow for the input of argument names for later
    SQL query preparation.
    For example::

        >>> statement, value = _transmute_filter('type', 'book')
        >>> statement.format('type_argument_one')
        >>> statement
        "portal_type = %(type_argument_one)s"

    And later when the DBAPI ``execute`` method works on this statement,
    it will supply an argument dictionary.
    ::

        >>> query = "SELECT * FROM modules WHERE {};".format(statement)
        >>> cursor.execute(query, dict(type_argument_one=value))
        >>> cursor.query
        "SELECT * FROM modules WHERE portal_type = 'Collection';"

    """
    if keyword not in VALID_FILTER_KEYWORDS:
        raise ValueError("Invalid filter keyword '{}'.".format(keyword))

    if keyword == 'type':
        value = value.lower()
        if value in ['book', 'collection']:
            type_name = 'Collection'
        elif value in ['page', 'module']:
            type_name = 'Module'
        else:
            raise ValueError("Invalid filter value '{}' for filter '{}'."
                             .format(value, keyword))
        return ('portal_type = %({})s', type_name)

    elif keyword == 'pubYear':
        return ('extract(year from revised) = %({})s', int(value))

    elif keyword == 'authorID':
        return ('%({})s = ANY(authors)', value)

    elif keyword == 'submitterID':
        return ('submitter = %({})s', value)

    return None, None


def _transmute_sort(sort_value):
    """Provide a value translation to the SQL column name."""
    try:
        return SORT_VALUES_MAPPING[sort_value.lower()]
    except KeyError:
        raise ValueError("Invalid sort key '{}' provided.".format(sort_value))


class WeightedSelect:
    """A SQL SELECT builder with weighted results."""

    def __init__(self, name, template, weight=0,
                 is_keyword_exclusive=True):
        self.name = name
        self.template = template
        self.weight = weight
        self.is_keyword_exclusive = is_keyword_exclusive

    def prepare(self, query):
        """Prepare the statement for DBAPI 2.0 execution.

        :returns: A tuple of the statement text and the arguments in an ordered
                  dictionary.
        """
        statements = []
        final_statement = None
        arguments = []

        for i, (keyword, value) in enumerate(query):
            if self.is_keyword_exclusive \
               and (keyword != self.name and keyword != WILDCARD_KEYWORD):
                continue
            argument_key = "{}_{}".format(self.name, i)
            stmt = self.template.format(argument_key)
            statements.append(stmt)
            arguments.append((argument_key, value))
        if statements:
            final_statement = SQL_WEIGHTED_SELECT_WRAPPER.format(
                self.weight,
                '\nUNION ALL\n'.join(statements))
        return (final_statement, OrderedDict(arguments))


def _make_weighted_select(name, weight=0):
    """Private factory for creation of WeightedSelect objects."""
    return WeightedSelect(name, SQL_SEARCH_TEMPLATES[name], weight)


def _build_search(structured_query, weights):
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
    statement = ''
    arguments = {}

    # Clone the weighted queries for popping.
    query_weight_order = DEFAULT_SEARCH_WEIGHTS.keys()

    # Roll over the weight sequence.
    query_list = []
    while query_weight_order:
        weight_name = query_weight_order.pop(0)
        if weights[weight_name]:
            weighted_select = _make_weighted_select(weight_name,
                                                    weights[weight_name])
            stmt, args = weighted_select.prepare(structured_query.terms)
            query_list.append(stmt)
            arguments.update(args)

    # get text terms and filter out common words
    text_terms = [term for ttype, term in structured_query.terms
                  if ttype == 'text']
    text_terms_wo_stopwords = [term for term in text_terms
                               if term.lower() not in STOPWORDS]
    # if there are other search terms (not type "text") or if the text
    # terms do not only consist of stopwords, then use the text terms
    # without stopwords
    if arguments or text_terms_wo_stopwords:
        text_terms = text_terms_wo_stopwords
    arguments.update({'text_terms': ' '.join(text_terms)})
    queries = '\nUNION ALL\n'.join([q for q in query_list if q is not None])

    # Add the arguments for filtering.
    filter_list = []
    if structured_query.filters:
        if len(filter_list) == 0:
            filter_list.append('')  # For SQL AND joining.
        for i, (keyword, value) in enumerate(structured_query.filters):
            arg_name = "{}_{}".format(keyword, i)
            # These key values are special in that they don't,
            #   directly translate to SQL fields and values.
            try:
                filter_stmt, match_value = _transmute_filter(keyword, value)
            except ValueError:
                del structured_query.filters[i]
                continue
            if filter_stmt:
                arguments[arg_name] = match_value
                filter_stmt = filter_stmt.format(arg_name)
                filter_list.append(filter_stmt)
    filters = ' AND '.join(filter_list)

    limits = ''
    groupby = ''
    having_list = []
    having = ''
    subject_filters = [v for k, v in structured_query.filters
                       if k == 'subject']
    if subject_filters:
        limits = 'NATURAL LEFT JOIN moduletags NATURAL LEFT JOIN tags'
        groupby = '''GROUP BY lm.name, lm.uuid, lm.portal_type, lm.authors,
             lm.major_version, lm.minor_version, language, lm.revised,
             ab.abstract, weight, rank, lm.module_ident, weighted.keys'''

        for subj in subject_filters:
            having_list.append("'{}' = ANY(array_agg(tag))".format(subj))
        having = 'HAVING ' + ' AND '.join(having_list)
    groupby = '\n'.join((groupby, having,))

    if not queries:  # all filter term case
        key_list = []
        for key, value in structured_query.filters:
            key_list.append(QUERY_FIELD_PAIR_SEPARATOR.join((value, key,)))
        keys = QUERY_FIELD_ITEM_SEPARATOR.join(key_list)
        queries = """\
SELECT module_ident, 1 AS weight, '{}'::text AS keys
FROM latest_modules""".format(keys)

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

    # Wrap the weighted queries with the main query.
    fmt_args = dict(limits=limits, queries=queries, filters=filters,
                    groupby=groupby, sorts=sorts)
    statement = SEARCH_QUERY.format(**fmt_args)
    return (statement, arguments)


def search(query, query_type=DEFAULT_QUERY_TYPE,
           weights=DEFAULT_SEARCH_WEIGHTS):
    """Search database using parsed query.

    Executes a database search query from the given ``query``
    (a ``Query`` object) and optionally accepts a list of search weights.
    By default, the search results are ordered by weight.

    :param query: containing terms, filters, and sorts.
    :type query: Query
    :param weights: weight values to assign to each keyword search field
    :type weights: dictionary of field names to weight integers
    :returns: a sequence of records that match the query conditions
    :rtype: QueryResults (which is a sequence of QueryRecord objects)
    """
    # Ensure all the weights are available, since the developer can supply
    #   a minimal set of weights. All missing weights become naught.
    weights = weights.copy()
    for default in [(key, 0) for key in DEFAULT_SEARCH_WEIGHTS]:
        weights.setdefault(*default)

    # Build the SQL statement.
    statement, arguments = _build_search(query, weights)

    # Execute the SQL.
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(statement, arguments)
            search_results = cursor.fetchall()
    # Wrap the SQL results.
    return QueryResults(search_results, query, query_type)
