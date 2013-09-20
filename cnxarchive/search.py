# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database search utilties"""
import os
import json
from collections import Mapping, OrderedDict, Sequence

import psycopg2
from cnxquerygrammar.query_parser import grammar, DictFormater

from . import get_settings
from .database import CONNECTION_SETTINGS_KEY, SQL_DIRECTORY
from .utils import (
    portaltype_to_mimetype, COLLECTION_MIMETYPE, MODULE_MIMETYPE,
    )


__all__ = ('search', 'Query',)


WILDCARD_KEYWORD = 'text'
VALID_FILTER_KEYWORDS = ('type',)
SORT_VALUES_MAPPING = {
    'pubdate': 'created',
    'version': 'version',
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
def _read_sql_file(name, root=SQL_SEARCH_DIRECTORY, extension='.sql'):
    path = os.path.join(root, '{}{}'.format(name, extension))
    with open(path, 'r') as fp:
        return fp.read()
SQL_SEARCH_TEMPLATES = {name: _read_sql_file(name, extension='.part.sql')
                        for name in DEFAULT_SEARCH_WEIGHTS.keys()}
SQL_WEIGHTED_SELECT_WRAPPER = _read_sql_file('wrapper')
QUERY_FIELD_ITEM_SEPARATOR = ';--;'
QUERY_FIELD_PAIR_SEPARATOR = '-::-'


class Query:
    """A structured respresentation of the query string"""

    def __init__(self, query):
        self.filters = [q for q in query if q[0] in VALID_FILTER_KEYWORDS]
        self.sorts = [q[1] for q in query if q[0] == 'sort']
        self.terms = [q for q in query
                      if q not in self.filters and q[0] != 'sort']

    @classmethod
    def from_raw_query(cls, query_string):
        """Given a raw string (typically typed by the user),
        parse to a structured format and initialize the class.
        """
        node_tree = grammar.parse(query_string)
        structured_query = DictFormater().visit(node_tree)
        return cls(structured_query)


class QueryRecord(Mapping):
    """A query record wrapper to parse hit values and add behavior."""

    def __init__(self, **kwargs):
        self._record = {k:v for k, v in kwargs.items()
                        if k not in ('_keys', 'matched', 'fields',)}
        self.matched = {}
        self.fields = {}
        # Parse the matching fields
        for field_record in kwargs['_keys'].split(QUERY_FIELD_ITEM_SEPARATOR):
            term, key = field_record.split(QUERY_FIELD_PAIR_SEPARATOR)
            self.matched.setdefault(term, set()).add(key)
            self.fields.setdefault(key, set()).add(term)
        self.match_hits = (self.matched, self.fields)

    def __getitem__(self, key):
        return self._record[key]

    def __iter__(self):
        return iter(self._record)

    def __len__(self):
        return len(self._record)

    @property
    def highlighted_abstract(self):
        """Highlight the found terms in the abstract text."""
        abstract = self['abstract']
        start_elm = '<span class=\"search-highlight\">'
        end_elm = '</span>'
        for term in self.fields['abstract']:
            start_at = 0
            term_len = len(term)
            while start_at < len(abstract):
                i = abstract.find(term, start_at)
                if i < 0: break
                abstract = abstract[:i] + start_elm \
                           + abstract[i:i+term_len] \
                           + end_elm + abstract[i+term_len:]
                start_at = i + len(start_elm) + term_len + len(end_elm)
        return abstract


class QueryResults(Sequence):
    """A listing of query results as well as hit counts and the parsed query
    string.
    """

    def __init__(self, rows):
        self._records = [QueryRecord(**r[0]) for r in rows]
        self.counts = {
            'mediaType': self._count_media(),
            'subject': self._count_field('subjects'),
            'keyword': self._count_field('keywords'),
            'author': self._count_authors(),
            'pubYear': self._count_publication_year(),
            }

    def __getitem__(self, index):
        return self._records[index]

    def __len__(self):
        return len(self._records)

    def _count_field(self, field_name):
        counts = {}
        for rec in self._records:
            for value in rec[field_name]:
                counts.setdefault(value, 0)
                counts[value] += 1
        return counts

    def _count_media(self):
        counts = {
            MODULE_MIMETYPE: 0,
            COLLECTION_MIMETYPE: 0,
            }
        for rec in self._records:
            counts[portaltype_to_mimetype(rec['mediaType'])] += 1
        return counts

    def _count_authors(self):
        counts = {}
        for rec in self._records:
            for author in rec['authors']:
                uid = author['id']
                counts.setdefault(uid, 0)
                counts[uid] += 1
        return counts

    def _count_publication_year(self):
        counts = {}
        for rec in self._records:
            date = rec['pubDate']
            if date is None:
                continue
            year = date[:4]
            counts.setdefault(year, 0)
            counts[year] += 1
        return counts


def _transmute_filter(keyword, value):
    """Provides a keyword to SQL column name translation for the filter."""
    # Since there is only one filter at this time, there is no need
    #   to over design this. Keeping this a simple switch over or error.
    if keyword not in VALID_FILTER_KEYWORDS:
        raise ValueError("Invalid filter keyword '{}'.".format(keyword))
    elif value != 'book':
        raise ValueError("Invalid filter value '{}' for filter '{}'." \
                             .format(value, keyword))
    return ('portal_type', 'Collection')


def _transmute_sort(sort_value):
    """Provides a value translation to the SQL column name."""
    try:
        return SORT_VALUES_MAPPING[sort_value.lower()]
    except KeyError:
        raise ValueError("Invalid sort key '{}' provided.".format(sort_value))


class WeightedSelect:
    """A SQL SELECT builder with weighted results"""

    def __init__(self, name, template, weight=0,
                 is_keyword_exclusive=True):
        self.name = name
        self.template = template
        self.weight = weight
        self.is_keyword_exclusive = is_keyword_exclusive

    def prepare(self, query):
        """Prepares the statement for DBAPI 2.0 execution.

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
    """Produces the search statement and argument dictionary to be executed
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
    queries = []
    while query_weight_order:
        weight_name = query_weight_order.pop(0)
        weighted_select = _make_weighted_select(weight_name,
                                                weights[weight_name])
        stmt, args = weighted_select.prepare(structured_query.terms)
        queries.append(stmt)
        arguments.update(args)
    queries = '\nUNION ALL\n'.join([q for q in queries if q is not None])

    # Add the arguments for filtering.
    filters = []
    if structured_query.filters:
        if len(filters) == 0: filters.append('')  # For AND joining.
        for i, (keyword, value) in enumerate(structured_query.filters):
            arg_name = "{}_{}".format(keyword, i)
            # These key values are special in that they don't,
            #   directly translate to SQL fields and values.
            field_name, match_value = _transmute_filter(keyword, value)
            arguments[arg_name] = match_value
            filter_stmt = "{} = %({})s".format(field_name, arg_name)
            filters.append(filter_stmt)
    filters = ' AND '.join(filters)
    # Add the arguments for sorting.
    sorts = []
    if structured_query.sorts:
        for sort in structured_query.sorts:
            field_name = _transmute_sort(sort)
            # These sort values are not the name of the column used
            #   in the database.
            stmt = "{} DESC".format(field_name)
            sorts.append(stmt)
    sorts.append('weight DESC')
    sorts = ', '.join(sorts)

    # Wrap the weighted queries with the main query.
    search_query_filepath = os.path.join(SQL_DIRECTORY,
                                         'search', 'query.sql')
    with open(search_query_filepath, 'r') as fb:
        statement = fb.read().format(queries, filters, sorts)
    return (statement, arguments)


def search(query, weights=DEFAULT_SEARCH_WEIGHTS):
    """Executes a database search query from the given ``query``
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
    settings = get_settings()
    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(statement, arguments)
            search_results = cursor.fetchall()

    # Wrap the SQL results.
    return QueryResults(search_results)
