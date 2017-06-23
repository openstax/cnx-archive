# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import testing as pyramid_testing

from .. import testing
from ... import config
from .views_test_data import COLLECTION_METADATA


class OaiViewsTestCase(unittest.TestCase):
    fixture = testing.data_fixture

    @classmethod
    def setUpClass(cls):
        cls.settings = testing.integration_test_settings()

    @testing.db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        self.request = pyramid_testing.DummyRequest()
        self.request.headers['HOST'] = 'cnx.org'
        self.request.application_url = 'http://cnx.org'
        config = pyramid_testing.setUp(settings=self.settings,
                                       request=self.request)

        # Set up routes
        from ... import declare_api_routes
        declare_api_routes(config)

        # Set up type info
        from ... import declare_type_info
        declare_type_info(config)

        # Clear all cached searches
        import memcache
        mc_servers = self.settings['memcache-servers'].split()
        mc = memcache.Client(mc_servers, debug=0)
        mc.flush_all()
        mc.disconnect_all()

        # Patch database search so that it's possible to assert call counts
        # later
        from ... import cache
        original_search = cache.database_search
        self.db_search_call_count = 0

        def patched_search(*args, **kwargs):
            self.db_search_call_count += 1
            return original_search(*args, **kwargs)
        cache.database_search = patched_search
        self.addCleanup(setattr, cache, 'database_search', original_search)

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    def test_oai_general(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'Identify'}

        from ...views.oai import oai
        oai = oai(self.request)
        self.assertTrue('dateTime' in oai.keys())
        self.assertEqual(oai['baseURL'], self.request.path_url)
        self.assertEqual(oai['query_request'], [{'name': 'verb', 'val': 'Identify'}])

    def test_oai_identify(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'Identify'}

        from ...views.oai import oai
        oai = oai(self.request)
        self.assertEqual(oai['host'], self.request.host)
        self.assertEqual(oai['adminEmail'], "support@openstax.org")
        self.assertEqual(oai['repository'], config.REPOSITORY_NAME)

    def test_oai_listIdentifiers(self):
        from_date = '2016-01-01'
        until_date = '2017-01-01'
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'ListIdentifiers',
                            'metadataPrefix': 'cnx_dc',
                            'until': until_date}

        from ...views.oai import oai
        oai = oai(self.request)
        for result in oai['results']:
            self.assertTrue(str(result['revised']) <= until_date)
            self.assertTrue(set(result.keys()) == set(["revised", "uuid"]))

    def test_oai_listMetadataFormats(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'ListMetadataFormats'}

        from ...views.oai import oai
        oai = oai(self.request)
        prefixes = [result['prefix'] for result in oai['results']]
        self.assertEqual(prefixes, ['oai_dc', 'ims1_2_1', 'cnx_dc'])

    def test_oai_listRecords(self):
        from_date = '2016-01-01'
        until_date = '2017-01-01'
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'ListRecords',
                            'metadataPrefix': 'cnx_dc',
                            'from': from_date,
                            'until': until_date}

        from ...views.oai import oai
        oai = oai(self.request)
        columns = set(['name', 'created', 'revised', 'uuid', 'link', 'portal_type',
                       'language', 'version', 'keywords', 'subjects',
                       'author_emails', 'authors', 'maintainers', 'translators',
                       'abstract', 'licenses_url'])
        for result in oai['results']:
            self.assertTrue(str(result['revised']) >= from_date and
                            str(result['revised']) <= until_date)
            self.assertEqual(set(result.keys()), columns)

    def test_oai_getRecord(self):
        uuid = COLLECTION_METADATA[u'id']
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        self.request.GET = {'verb': 'GetRecord',
                            'metadataPrefix': 'cnx_dc',
                            'identifier': "oai:{}:{}".format(self.request.host, uuid)}

        from ...views.oai import oai
        oai = oai(self.request)
        self.assertEqual(len(oai['results']), 1)
        self.assertEqual(oai['results'][0]['uuid'], uuid)

    def test_oai_errors(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'oai'
        from ...views.oai import oai

        # Invalid Verb
        self.request.GET = {'verb': 'FakeVerb'}
        oai_0 = oai(self.request)
        self.assertEqual(oai_0['error']['code'], 'badVerb')

        # Missing a required argument
        self.request.GET = {'verb': 'ListRecords'}
        oai_1 = oai(self.request)
        self.assertEqual(oai_1['error'], {'code': 'badArgument',
                                          'message': 'Required argument {} missing'.
                                                     format(['metadataPrefix'])})
        # Invalid argument
        self.request.GET = {'verb': 'Identify', 'fake': 'test'}
        oai_2 = oai(self.request)
        self.assertEqual(oai_2['error'], {'code': 'badArgument',
                                          'message': 'Illegal arguments: {}'.
                                                     format(['fake'])})

        # Invalid MetadataPrefix
        self.request.GET = {'verb': 'ListIdentifiers', 'metadataPrefix': 'fake'}
        oai_3 = oai(self.request)
        self.assertEqual(oai_3['error'], {'code': 'cannotDisseminateFormat',
                                          'message': 'metadataPrefix {} not supported'.
                                                     format('fake')})

        # Invalid Identifier
        identifier = 'fake_identifier'
        self.request.GET = {'verb': 'GetRecord', 'metadataPrefix': 'cnx_dc',
                            'identifier': identifier}
        oai_4 = oai(self.request)
        self.assertEqual(oai_4['error'], {'code': 'idDoesNotExist',
                                          'message': "id does not exist {}".
                                                     format(identifier)})

        # ListRecords no Records match
        self.request.GET = {'verb': 'ListRecords', 'metadataPrefix': 'oai_dc',
                            'from': '2017-01-02', 'until': '2017-01-01'}
        oai_5 = oai(self.request)
        self.assertEqual(oai_5['error'], {'code': 'noRecordsMatch',
                                          'message': 'No matches for the given request'})

        # ListIdentifiers no Records match
        self.request.GET = {'verb': 'ListIdentifiers', 'metadataPrefix': 'ims1_2_1',
                            'from': '2017-01-02', 'until': '2017-01-01'}
        oai_6 = oai(self.request)
        self.assertEqual(oai_6['error'], {'code': 'noRecordsMatch',
                                          'message': 'No matches for the given request'})

        # IdDoesNotExist error
        identifier = 'oai:{}:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'.format(self.request.host)
        self.request.GET = {'verb': 'GetRecord', 'metadataPrefix': 'cnx_dc',
                            'identifier': identifier}
        oai_6 = oai(self.request)
        self.assertEqual(oai_6['error'], {'code': 'idDoesNotExist',
                                          'message': 'id does not exist {}'.
                                                     format(identifier)})
