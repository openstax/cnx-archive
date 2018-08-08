# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import json
import datetime
import unittest
import uuid

import psycopg2
from pyramid import testing as pyramid_testing

from . import testing


RAW_SEARCH_ROWS_FILEPATH = os.path.join(testing.DATA_DIRECTORY,
                                        'raw-search-rows.json')
with open(RAW_SEARCH_ROWS_FILEPATH, 'r') as fb:
    # Search results for a search on 'physics'.
    RAW_QUERY_RECORDS = json.load(fb)


class QueryTestCase(unittest.TestCase):
    """Test the non-grammar related functionality of the Query class."""

    @property
    def target_cls(self):
        from ..search import Query
        return Query

    def call_target(self, *args, **kwargs):
        return self.target_cls.from_raw_query(*args, **kwargs)

    def test_stopword_elimination(self):
        """Verify the removal of stopwords from the query."""
        raw_query = "The Cat in the Hat"
        query = self.call_target(raw_query)

        expected = [('text', 'Cat'), ('text', 'Hat')]
        self.assertEqual(expected, query.terms)

    def test_w_single_letter_stopwords(self):
        raw_query = "I am a dog"
        query = self.call_target(raw_query)

        expected = [('text', 'dog')]
        self.assertEqual(expected, query.terms)


class BaseSearchTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        config = pyramid_testing.setUp(settings=self.settings)
        self.fixture.setUp()

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()


class SearchModelTestCase(BaseSearchTestCase):

    def make_queryrecord(self, *args, **kwargs):
        from ..search import QueryRecord
        return QueryRecord(*args, **kwargs)

    def make_queryresults(self, *args, **kwargs):
        from ..search import QueryResults
        return QueryResults(*args, **kwargs)

    def test_summary_highlighting(self):
        # Confirm the record highlights on found terms in the abstract/summary.
        record = self.make_queryrecord(**RAW_QUERY_RECORDS[0][0])

        expected = """algebra-based, two-semester college <b>physics</b> book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental \
<b>physics</b> concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities \
to solve traditional <b>physics</b> application problems."""
        self.assertEqual(record.highlighted_abstract, expected)

    def test_fulltext_highlighting(self):
        # Confirm the record highlights on found terms in the fulltext.
        record = self.make_queryrecord(**RAW_QUERY_RECORDS[0][0])

        expected = None
        # XXX Something wrong with the data, but otherwise this works as
        #     expected.
        self.assertEqual(record.highlighted_fulltext, expected)

    def test_result_counts(self):
        # Set the test to return top 5 keywords
        from .. import search
        old_max_values_for_keywords = search.MAX_VALUES_FOR_KEYWORDS

        def reset_max_values_for_keywords():
            search.MAX_VALUES_FOR_KEYWORDS = old_max_values_for_keywords
        self.addCleanup(reset_max_values_for_keywords)
        search.MAX_VALUES_FOR_KEYWORDS = 5

        # Verify the counts on the results object.
        query = [('text', 'physics')]
        results = self.make_queryresults(RAW_QUERY_RECORDS, query)

        self.assertEqual(len(results), 15)
        # Check the type counts.
        from ..utils import MODULE_MIMETYPE, COLLECTION_MIMETYPE
        types = results.counts['type']
        self.assertEqual(types, [
            (COLLECTION_MIMETYPE, 1,),
            (MODULE_MIMETYPE, 14,),
            ])
        # Check the author counts
        osc_physics = {u'firstname': u'College',
                       u'fullname': u'OSC Physics Maintainer',
                       u'id': u'cnxcap',
                       u'surname': u'Physics',
                       u'title': None,
                       }
        open_stax_college = {u'surname': None,
                             u'firstname': u'OpenStax College',
                             u'title': None,
                             u'id': u'OpenStaxCollege',
                             u'fullname': u'OpenStax College',
                             }
        expected = [(open_stax_college['id'], 15,), (osc_physics['id'], 1,)]
        self.assertEqual(results.counts['authorID'], expected)

        # Check counts for publication year.
        pub_years = list(results.counts['pubYear'])
        self.assertEqual(pub_years, [(u'2013', 12), (u'2012', 1), (u'2011', 2)])

        # Check the subject counts.
        subjects = dict(results.counts['subject'])
        self.assertEqual(subjects,
                         {u'Mathematics and Statistics': 8,
                          u'Science and Technology': 7,
                          })

        # Check the keyword counts.
        keywords = results.counts['keyword']
        self.assertEqual(len(keywords), 5)
        self.assertEqual(keywords, [(u'force', 3),
                                    (u'friction', 4),
                                    (u'Modern physics', 2),
                                    (u'Quantum mechanics', 2),
                                    (u'Scientific method', 2),
                                    ])

    def test_result_counts_with_author_limit(self):
        # Set the test to return top 1 author
        from .. import search
        old_max_values_for_authors = search.MAX_VALUES_FOR_AUTHORS
        self.addCleanup(setattr, search, 'MAX_VALUES_FOR_AUTHORS',
                        old_max_values_for_authors)
        search.MAX_VALUES_FOR_AUTHORS = 1

        query = [('text', 'physics')]
        results = self.make_queryresults(RAW_QUERY_RECORDS, query)

        open_stax_college = {
            u'surname': None,
            u'suffix': None,
            u'firstname': u'OpenStax College',
            u'title': None,
            u'id': u'OpenStaxCollege',
            u'fullname': u'OpenStax College',
            }

        # Check there is only one author returned
        authors = results.counts['authorID']
        self.assertEqual(authors, [(open_stax_college['id'], 15,)])

    def test_auxiliary_authors(self):
        # Check that the query results object contains a list of all the
        #   authors that appear in the results.
        from .. import search
        query = [('text', 'physics')]
        results = self.make_queryresults(RAW_QUERY_RECORDS, query)

        # Simple quantity check before quality.
        authors = results.auxiliary['authors']
        self.assertEqual(len(authors), 2)
        # Check the contents after sorting the results.
        authors = sorted(authors, key=lambda x: x['id'])
        expected = [
            {u'surname': None,
             u'firstname': u'OpenStax College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OpenStax College',
             u'id': u'OpenStaxCollege',
             },
            {u'surname': u'Physics',
             u'firstname': u'College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OSC Physics Maintainer',
             u'id': u'cnxcap',
             },
            ]
        self.assertEqual(authors, expected)


class SearchTestCase(BaseSearchTestCase):

    def call_target(self, query_params, query_type=None, weights=None):
        from ..search import DEFAULT_QUERY_TYPE, DEFAULT_SEARCH_WEIGHTS
        if query_type is None:
            query_type = DEFAULT_QUERY_TYPE
        if weights is None:
            weights = DEFAULT_SEARCH_WEIGHTS

        # Single point of import failure.
        from ..search import search, Query
        self.query = Query(query_params)
        self.addCleanup(delattr, self, 'query')
        return search(self.query, query_type=query_type)

    def test_utf8_search(self):
        query_params = [('text', 'Indkøb')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 1)

    def test_search_w_stopwords(self):
        # wildcard search terms have stopwords removed
        query_params = [('text', 'seek'), ('text', 'to'), ('text', 'reduce')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 3)

    def test_search_w_only_stopwords(self):
        # wildcard search terms with only stopwords are not removed
        query_params = [('text', 'and'), ('text', 'the')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 0)

    def test_search_title_w_stopwords(self):
        # search terms for specific fields are not removed even if stopwords
        # are present
        query_params = [('title', 'the')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 2)

    def test_title_search_utf8(self):
        query_params = [('title', 'Indkøb')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 1)

    def test_title_search(self):
        # Simple case to test for results of a basic title search.
        query_params = [('title', 'Physics')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 5)

    def test_abstract_search(self):
        # Test for result on an abstract search.
        query_params = [('abstract', 'algebra')]
        results = self.call_target(query_params)

        self.assertEqual(len(results), 2)

    def _add_dummy_user(self):
        """Method to add a user and return that user's info."""
        info = {
            'username': 'jmiller',
            'first_name': 'Jill',
            'last_name': 'Miller',
            'full_name': 'Jill S. Miller',
            'title': None,
            }

        # Create a new user.
        with self.fixture.start_db_connection() as db_connection:
            with db_connection.cursor() as accounts_cursor:
                accounts_cursor.execute("""\
INSERT INTO users
  (username, first_name, last_name, full_name)
  VALUES
  (%(username)s, %(first_name)s, %(last_name)s, %(full_name)s)
  RETURNING username""", info)
        return info

    @testing.db_connect
    def test_author_search(self, cursor):
        # Test the results of an author search.
        user_info = self._add_dummy_user()
        # we want to make sure an author can be searched by first and last name
        # even if they have a middle initial
        query_params = [('author', 'Jill Miller')]

        # Update two modules in include this user as an author.
        cursor.execute(
            "UPDATE latest_modules SET (authors) = (%s) "
            "WHERE module_ident = %s OR module_ident = %s;",
            ([user_info['username']], 2, 3,))
        cursor.connection.commit()

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_fulltext_search(self):
        # Test the results of a search on fulltext.
        query_params = [('text', 'isomeric')]

        results = self.call_target(query_params)
        self.assertEqual(len(results), 3)
        # Ensure the record with both values is the only result.
        self.assertEqual(results[0]['id'],
                         'e79ffde3-7fb4-4af3-9ec8-df648b391597')

    def test_type_filter_on_books(self):
        # Test for type filtering that will find books only.
        query_params = [('text', 'physics'), ('type', 'book')]

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]['id'] in
                        ['e79ffde3-7fb4-4af3-9ec8-df648b391597',
                        'a733d0d2-de9b-43f9-8aa9-f0895036899e'])

    def test_type_filter_on_pages(self):
        # Test for type filtering that will find books only.
        query_params = [('text', 'physics'), ('type', 'page')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 8)
        # Check that the collection/book is not in the results.
        self.assertNotIn('e79ffde3-7fb4-4af3-9ec8-df648b391597',
                         result_ids)

    def test_type_filter_case_insensitive(self):
        query_params = [('text', 'physics'), ('type', 'Book')]

        results = self.call_target(query_params)
        self.assertEqual(len(results), 2)

    def test_type_filter_on_unknown(self):
        # Test for type filtering on an unknown type.
        query_params = [('text', 'physics'), ('type', 'image')]

        results = self.call_target(query_params)
        # Check for the removal of the filter
        self.assertEqual(self.query.filters, [])

    @testing.db_connect
    def _pubYear_setup(self, cursor):
        # Modify some modules to give them different year of publication
        pub_year_mods = {
            '2010': ['e79ffde3-7fb4-4af3-9ec8-df648b391597',
                     '209deb1f-1a46-4369-9e0d-18674cf58a3e'],
            '2012': ['f3c9ab70-a916-4d8c-9256-42953287b4e9'],
            }

        for year, ids in pub_year_mods.iteritems():
            cursor.execute(
                "UPDATE latest_modules "
                "SET revised = '{}-07-31 12:00:00.000000-07'"
                "WHERE uuid IN %s RETURNING module_ident".format(year),
                [tuple(ids)])

    def test_pubYear_limit(self):
        self._pubYear_setup()

        # Test for limit only results with pubYear 2013
        query_params = [('pubYear', '2013')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 13)
        self.assertNotIn('e79ffde3-7fb4-4af3-9ec8-df648b391597', result_ids)
        self.assertNotIn('209deb1f-1a46-4369-9e0d-18674cf58a3e', result_ids)
        self.assertNotIn('f3c9ab70-a916-4d8c-9256-42953287b4e9', result_ids)

    def test_pubYear_filter(self):
        self._pubYear_setup()

        # Test for filtering results with pubYear 2013
        query_params = [('text', 'physics'), ('pubYear', '2013')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 7)
        self.assertNotIn('e79ffde3-7fb4-4af3-9ec8-df648b391597', result_ids)
        self.assertNotIn('209deb1f-1a46-4369-9e0d-18674cf58a3e', result_ids)
        self.assertNotIn('f3c9ab70-a916-4d8c-9256-42953287b4e9', result_ids)

    def test_pubYear_filter_no_results(self):
        self._pubYear_setup()

        # Test for filtering results with pubYear 2011
        query_params = [('text', 'physics'), ('pubYear', '2011')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 0)
        self.assertEqual(result_ids, [])

    def test_pubYear_without_term(self):
        self._pubYear_setup()
        query_params = [('pubYear', '2010')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 2)
        self.assertEqual(result_ids, ['e79ffde3-7fb4-4af3-9ec8-df648b391597',
                                      '209deb1f-1a46-4369-9e0d-18674cf58a3e'])

    @testing.db_connect
    def test_pubYear_w_timezone(self, cursor):
        """Verify the use of pubYear with timestamps that occur 12/31 or 1/1."""
        # See also https://github.com/Connexions/cnx-archive/issues/249
        # Change the local tzinfo to be near 'America/Whitehorse'.
        from .. import search
        self.addCleanup(setattr, search, 'LOCAL_TZINFO', search.LOCAL_TZINFO)
        from psycopg2.tz import FixedOffsetTimezone
        local_tz = FixedOffsetTimezone(-8 * 60)
        setattr(search, 'LOCAL_TZINFO', local_tz)

        # Modify some modules to give them different year of publication.
        # All these dates occur in 2020 according to the system time zone.
        pub_year_mods = [
            ('e79ffde3-7fb4-4af3-9ec8-df648b391597',
             # Almost 2021 somewhere in mid-USA
             datetime.datetime(2020, 12, 31, 23, 5, 0,
                               tzinfo=FixedOffsetTimezone(-6 * 60)),),
            ('209deb1f-1a46-4369-9e0d-18674cf58a3e',
             # Just turned 2021 somewhere in mid-USA
             datetime.datetime(2021, 1, 1, 0, 5, 0,
                               tzinfo=FixedOffsetTimezone(-6 * 60)),),
            ('f3c9ab70-a916-4d8c-9256-42953287b4e9',
             # Almost 2020 in Alaska
             datetime.datetime(2019, 12, 31, 23, 5, 0,
                               tzinfo=FixedOffsetTimezone(-10 * 60)),),
            ]

        for id, date in pub_year_mods:
            cursor.execute(
                "UPDATE latest_modules "
                "SET revised = %s "
                "WHERE uuid = %s", (date, id,))
        cursor.connection.commit()

        query_params = [('pubYear', '2020')]
        results = self.call_target(query_params)

        self.assertEqual(results.counts['pubYear'], [(u'2020', 3)])

    def test_type_without_term(self):
        query_params = [('type', 'book')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 2)
        self.assertEqual(result_ids, ['e79ffde3-7fb4-4af3-9ec8-df648b391597',
                                      'a733d0d2-de9b-43f9-8aa9-f0895036899e'])

    def test_authorId_filter(self):
        # Filter results by author "OSC Physics Maintainer"
        query_params = [('text', 'physics'),
                        ('authorID', 'cnxcap')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 1)
        self.assertEqual(result_ids, ['209deb1f-1a46-4369-9e0d-18674cf58a3e'])

    @testing.db_connect
    def _language_setup(self, cursor):
        # Modify some modules to give them different languages
        language_mods = {
            'fr': ['209deb1f-1a46-4369-9e0d-18674cf58a3e'],
            }

        for language, ids in language_mods.iteritems():
            cursor.execute(
                "UPDATE latest_modules "
                "SET language = %s"
                "WHERE uuid IN %s RETURNING module_ident",
                [language, tuple(ids)])

    def test_language_without_term(self):
        self._language_setup()
        query_params = [('language', 'fr')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 1)
        self.assertEqual(result_ids, ['209deb1f-1a46-4369-9e0d-18674cf58a3e'])

    def test_term_and_subject(self):
        query_params = [('text', 'physics'),
                        ('subject', 'Science and Technology')]

        results = self.call_target(query_params)
        self.assertEqual(len(results), 3)

    def test_weighted_by_derivation_count(self):
        """Verify weighted results by the number of derived works."""
        query_params = [('type', 'book')]

        results = self.call_target(query_params)
        result_weights = [(r['id'], r['weight']) for r in results]
        self.assertEqual(len(results), 2)
        # Both of these are books, the a733d0d2 is derived from e79ffde3.
        # Because the a733d0d2 has derived parentage, it get's a penalty.
        expected = [(u'e79ffde3-7fb4-4af3-9ec8-df648b391597', 0),
                    (u'a733d0d2-de9b-43f9-8aa9-f0895036899e', -1),
                    ]
        self.assertEqual(result_weights, expected)

    def test_subject_and_subject(self):
        query_params = [('subject', 'Science and Technology'),
                        ('subject', 'Mathematics and Statistics')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(results), 1)
        self.assertEqual(result_ids, ['e79ffde3-7fb4-4af3-9ec8-df648b391597'])

    def test_subject_authorID_term(self):
        query_params = [('text', 'physics'),
                        ('subject', 'Mathematics and Statistics'),
                        # "OSC Physics Maintainer"
                        ('authorID', 'cnxcap')]

        results = self.call_target(query_params)
        result_ids = [r['id'] for r in results]
        self.assertEqual(len(result_ids), 1)
        self.assertEqual(result_ids, ['209deb1f-1a46-4369-9e0d-18674cf58a3e'])

    @testing.db_connect
    def test_sort_filter_on_pubdate(self, cursor):
        # Test the sorting of results by publication date.
        query_params = [('text', 'physics'), ('sort', 'pubDate')]
        _same_date = '2113-01-01 00:00:00 America/New_York'
        expectations = [
                        ('a733d0d2-de9b-43f9-8aa9-f0895036899e',
                         _same_date,),  # this one has a higher weight.
                        ('e79ffde3-7fb4-4af3-9ec8-df648b391597',
                         _same_date,),
                        # first return all the books, then all the pages
                        ('d395b566-5fe3-4428-bcb2-19016e3aa3ce',
                         _same_date,),  # this one has a higher weight.
                        ('c8bdbabc-62b1-4a5f-b291-982ab25756d7',
                         _same_date,),
                        ('5152cea8-829a-4aaf-bcc5-c58a416ecb66',
                         '2112-01-01 00:00:00 America/New_York',),
                        ]

        # Update two modules in include a creation date.
        for id, date in expectations:
            cursor.execute(
                "UPDATE latest_modules SET (revised) = (%s) "
                "WHERE uuid = %s::uuid;", (date, id))
        cursor.connection.commit()

        results = self.call_target(query_params)
        self.assertEqual(len(results), 10)
        for i, (id, date) in enumerate(expectations):
            self.assertEqual(results[i]['id'], id)

    @testing.db_connect
    def test_sort_filter_on_popularity(self, cursor):
        # Test the sorting of results by popularity (hit statistics).
        query_params = [('text', 'physics'), ('sort', 'popularity')]
        # The top three items we are looking have their normal sort
        #   index in a comment to the left, just to show where it came from.
        expectations = [
            # ident: uuid
            # books first
            (1, u'e79ffde3-7fb4-4af3-9ec8-df648b391597',),
            # books with no hits applied, normal ordering expected.
            (18, u'a733d0d2-de9b-43f9-8aa9-f0895036899e',),
            # then pages
            (3, u'f3c9ab70-a916-4d8c-9256-42953287b4e9',),
            (7, u'5838b105-41cd-4c3d-a957-3ac004a48af3',),
            # No hits applied from here on, normal ordering expected.
            (9, u'ea271306-f7f2-46ac-b2ec-1d80ff186a59',),
        ]
        hits_to_apply = {3: 25, 7: 15, 9: 0, 1: 10, 18: 0}

        from datetime import datetime, timedelta
        end = datetime.today()
        start = end - timedelta(1)
        for ident, hits in hits_to_apply.items():
            cursor.execute("INSERT INTO document_hits "
                           "VALUES (%s, %s, %s, %s);",
                           (ident, start, end, hits,))
            cursor.execute("SELECT update_hit_ranks();")
        cursor.connection.commit()

        results = self.call_target(query_params)
        for i, (ident, id) in enumerate(expectations):
            self.assertEqual(results[i]['id'], id)

    def test_anding(self):
        # Test that the results intersect with one another rather than
        #   search the terms independently. This uses the AND operator.
        # The query for this would look like "physics [AND] force".
        query_params = [('text', 'physics'), ('text', 'concepts'),
                        ('keyword', 'approximation'),
                        ]
        expectations = ['f3c9ab70-a916-4d8c-9256-42953287b4e9',
                        '5838b105-41cd-4c3d-a957-3ac004a48af3',
                        ]

        results = self.call_target(query_params, query_type='AND')
        # Basically, everything matches the first search term,
        #   about eleven match the first two terms,
        #   and when the third is through in we condense this to two.
        self.assertEqual(len(results), 2)
        for i, id in enumerate(expectations):
            self.assertEqual(results[i]['id'], id)
