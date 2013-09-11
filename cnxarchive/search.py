# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Database search utilties"""
import os
from collections import OrderedDict
import psycopg2

from . import get_settings
from .database import CONNECTION_SETTINGS_KEY, SQL_DIRECTORY


WILDCARD_KEYWORD = 'text'
VALID_FILTER_KEYWORDS = ('type',)
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


class DBQuery:
    """Builds a database search query from a dictionary of field
    denoted values.
    """

    def __init__(self, query, weights={}):
        self.filters = [q for q in query if q[0] in VALID_FILTER_KEYWORDS]
        self.query = [q for q in query if q not in self.filters]
        self.weights = weights
        if not self.weights:
            # Without any predefined weights, use the defaults verbatim.
            defaults = DEFAULT_SEARCH_WEIGHTS
        else:
            defaults = {key:0 for key in DEFAULT_SEARCH_WEIGHTS}
        for default in defaults.iteritems():
            self.weights.setdefault(*default)
        self._query_weight_order = DEFAULT_SEARCH_WEIGHTS.keys()

    def __call__(self):
        """Return the search results"""
        settings = get_settings()
        with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(*self.dbapi_args)
                query_results = cursor.fetchall()
        return query_results

    @property
    def dbapi_args(self):
        """Produces a value that can be input directly to the DBAPI v2
        execute method. For example, ``cursor.execute(*db_query.dbapi_args)``
        """
        statement = ''
        arguments = {}

        # Clone the weighted queries for popping.
        weights = self._query_weight_order[:]

        # Roll over the weight sequence.
        queries = []
        while weights:
            weight_name = weights.pop(0)
            weighted_select = _make_weighted_select(weight_name,
                                                    self.weights[weight_name])
            stmt, args = weighted_select.prepare(self.query)
            queries.append(stmt)
            arguments.update(args)
        queries = '\nUNION ALL\n'.join([q for q in queries if q is not None])

        # Add the arguments for filtering
        filters = []
        if self.filters:
            if len(filters) == 0: filters.append('')  # For AND joining.
            for i, (keyword, value) in enumerate(self.filters):
                arg_name = "{}_{}".format(keyword, i)
                # These key values are special in that they don't,
                #   directly translate to SQL fields and values.
                field_name, match_value = _transmute_filter(keyword, value)
                arguments[arg_name] = match_value
                filter_stmt = "{} = %({})s".format(field_name, arg_name)
                filters.append(filter_stmt)
        filters = ' AND '.join(filters)

        # Wrap the weighted queries with the main query.
        search_query_filepath = os.path.join(SQL_DIRECTORY,
                                             'search', 'query.sql')
        with open(search_query_filepath, 'r') as fb:
            statement = fb.read().format(queries, filters)

        return (statement, arguments)
