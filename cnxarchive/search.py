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


class DBQuery:
    """Builds a database search query from a dictionary of field
    denoted values.
    """

    def __init__(self, query, weights={}):
        self.query = query
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
        args = {}

        # Build the weighted queries.
        weights = self._query_weight_order[:]
        wrapper_filepath = os.path.join(SQL_DIRECTORY, 'search', 'wrapper.sql')
        with open(wrapper_filepath, 'r') as fb:
            wrapper_template = fb.read()
        # Roll over the weight sequence.
        queries = []
        while weights:
            # TODO Bail out early if none of the remaining weights have
            #      any weight value.
            weight = weights.pop(0)
            sub_queries = []
            # Build the individual sub_queries.
            for i, (key, item) in enumerate(self.query):
                arg_key = "{}_{}".format(weight, i)
                sql_filename = "{}.part.sql".format(weight)
                sql_filepath = os.path.join(SQL_DIRECTORY,
                                            'search', sql_filename)
                with open(sql_filepath, 'r') as sql_file:
                    sub_query = sql_file.read().format(arg_key)
                args[arg_key] = item
                sub_queries.append(sub_query)

            # Wrap the unioned queries in the outter select.
            query = wrapper_template.format(self.weights[weight],
                                            '\nUNION ALL\n'.join(sub_queries))
            queries.append(query)
        queries = '\nUNION ALL\n'.join(queries)

        # Wrap the weighted queries with the main query.
        search_query_filepath = os.path.join(SQL_DIRECTORY,
                                             'search', 'query.sql')
        with open(search_query_filepath, 'r') as fb:
            statement = fb.read().format(queries)

        return (statement, args)
