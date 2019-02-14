# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2019, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest
import pytest
from pyramid import testing
from ...views.content import get_content

class ContentPyramidTestCase(unittest.TestCase):
    def setUp(self):
        self.request = testing.DummyRequest()
        #self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    #def test_content_view(self):
    #    #request = testing.DummyRequest()
    #    uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
    #    version = '6.1'
    #
    #    # Build the request environment.
    #    self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
    #    info = get_content(self.request)
    #    print 'Results: ' + str(info)

    @pytest.fixture()
    def testapp(self):
        """Create an instance of our app for testing."""
        from cnxarchive import main
        app = main({})
        from webtest import TestApp
        return TestApp(app)

    #@pytest.fixture(name="testapp")
    #def get_testapp(self):
    #    return testapp()
    
    def test_cache_control(testapp):
        #from .views import ENTRIES
        response = testapp.get('/e79ffde3-7fb4-4af3-9ec8-df648b391597', status=200)
        print 'response: ' + str(response)
        #html = response.html
        #assert len(ENTRIES) == len(html.findAll("article"))
