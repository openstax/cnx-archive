# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import datetime
import glob
import HTMLParser
import time
import json
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing
from pyramid.encode import url_quote
from pyramid.traversal import PATH_SAFE

from ..utils import IdentHashShortId, IdentHashMissingVersion
from . import testing


def quote(path):
    """URL encode the path"""
    return url_quote(path, safe=PATH_SAFE)


COLLECTION_METADATA = {
    u'roles': None,
    u'subjects': [u'Mathematics and Statistics', u'Science and Technology', u'OpenStax Featured'],
    u'abstract': u'<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" '
                 u'xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">'
                 u'This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, '
                 u'fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample '
                 u'practice opportunities to solve traditional physics application problems.</div>',
    u'authors': [{u'id': u'OpenStaxCollege',
                  u'fullname': u'OpenStax College',
                  u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  }],
    u'created': u'2013-07-31T19:07:20Z',
    u'doctype': u'',
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'shortId': u'55_943-0',
    u'language': u'en',
    u'license': {
        u'code': u'by',
        u'version': u'4.0',
        u'name': u'Creative Commons Attribution License',
        u'url': u'http://creativecommons.org/licenses/by/4.0/',
        },
    u'licensors': [{u'surname': u'University',
                    u'firstname': u'Rice',
                    u'suffix': None,
                    u'title': None,
                    u'id': u'OSCRiceUniversity',
                    u'fullname': u'Rice University',
                    },
                   ],
    u'publishers': [{u'surname': None,
                     u'firstname': u'OpenStax College',
                     u'suffix': None,
                     u'title': None,
                     u'id': u'OpenStaxCollege',
                     u'fullname': u'OpenStax College',
                     },
                    {u'surname': u'Physics',
                     u'firstname': u'College',
                     u'suffix': None,
                     u'title': None,
                     u'id': u'cnxcap',
                     u'fullname': u'OSC Physics Maintainer',
                     }
                    ],
    u'title': u'College Physics',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentTitle': None,
    u'parentVersion': '',
    u'parent': {
        u'authors': [],
        u'id': None,
        u'shortId': None,
        u'title': None,
        u'version': '',
        },
    u'revised': u'2013-08-31T19:07:20Z',
    u'stateid': 1,
    u'submitlog': u'New version 1.7',
    u'submitter': {
        u'surname': None,
        u'firstname': u'OpenStax College',
        u'suffix': None,
        u'title': None,
        u'id': u'OpenStaxCollege',
        u'fullname': u'OpenStax College',
        },
    u'mediaType': u'application/vnd.org.cnx.collection',
    u'version': u'7.1',
    u'printStyle': None,
    u'googleAnalytics': u'UA-XXXXX-Y',
    u'buyLink': None,
    u'legacy_id': u'col11406',
    u'legacy_version': u'1.7',
    u'history': [
        {
            u'version': u'7.1',
            u'revised': u'2013-08-31T19:07:20Z',
            u'changes': 'New version 1.7',
            u'publisher': {
                u'surname': None,
                u'firstname': u'OpenStax College',
                u'suffix': None,
                u'title': None,
                u'id': u'OpenStaxCollege',
                u'fullname': u'OpenStax College',
                },
            },
        {
            u"version": u"6.2",
            u"revised": u"2013-08-02T01:02:23Z",
            u"changes": u"Add second collated version",
            u"publisher": {
                u"surname": None,
                u"firstname": "OpenStax College",
                u"suffix": None,
                u"title": None,
                u"id": "OpenStaxCollege",
                u"fullname": "OpenStax College",
                },
            },
        {
            u'version': u'6.1',
            u'revised': u'2013-07-31T19:07:20Z',
            u'changes': 'Updated something',
            u'publisher': {
                u'surname': None,
                u'firstname': u'OpenStax College',
                u'suffix': None,
                u'title': None,
                u'id': u'OpenStaxCollege',
                u'fullname': u'OpenStax College',
                },
            },
        ],
    u'keywords': [
        u'college physics', u'physics', u'friction', u'ac circuits',
        u'atomic physics', u'bioelectricity',
        u'biological and medical applications', u'circuits',
        u'collisions', u'dc instruments', u'drag', u'elasticity',
        u'electric charge and electric field', u'electric current',
        u'electric potential', u'electrical technologies',
        u'electromagnetic induction', u'electromagnetic waves', u'energy',
        u'fluid dynamics', u'fluid statics', u'forces', u'frontiers of physics',
        u'gas laws', u'geometric optics', u'heat and transfer methods',
        u'kinematics', u'kinetic theory', u'linear momentum', u'magnetism',
        u'medical applications of nuclear physics',
        u'Newton\u2019s Laws of Motion', u'Ohm\u2019s Law',
        u'oscillatory motion and waves', u'particle physics',
        u'physics of hearing', u'quantum physics',
        u'radioactivity and nuclear physics', u'resistance',
        u'rotational motion and angular momentum', u'special relativity',
        u'statics and torque', u'temperature', u'thermodynamics',
        u'uniform circular motion and gravitation',
        u'vision and optical instruments', u'wave optics', u'work',
        ],
    u'resources': [
        # FIXME This file probably shouldn't exist?
        {u'filename': u'collection.html',
         u'id': u'271b03b039158a5ff77937adf05f398dfc4f9929',
         u'media_type': u'text/xml',
         },
        {u'filename': u'collection.xml',
         u'id': u'271b03b039158a5ff77937adf05f398dfc4f9929',
         u'media_type': u'text/xml',
         },
        {u'filename': u'featured-cover.png',
         u'id': u'6214e8dcdf2824dbf830b4a0d77a3fa2f53608d2',
         u'media_type': u'image/png',
         },
        ],
    u'collated': False,
    }
COLLECTION_JSON_TREE = {
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
    u'shortId': u'55_943-0@7.1',
    u'title': u'College Physics',
    u'contents': [
        {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
         u'shortId': u'IJ3rHxpG@7',
         u'title': u'Preface'},
        {u'id': u'subcol',
         u'shortId': u'subcol',
         u'title': u'Introduction: The Nature of Science and Physics',
         u'contents': [
                {u'id': u'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
                 u'shortId': u'88mrcKkW@3',
                 u'title': u'Introduction to Science and the Realm of Physics, Physical Quantities, and Units'},
                {u'id': u'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
                 u'shortId': u'05W1Zl_j@4',
                 u'title': u'Physics: An Introduction'},
                {u'id': u'c8bdbabc-62b1-4a5f-b291-982ab25756d7@6',
                 u'shortId': u'yL26vGKx@6',
                 u'title': u'Physical Quantities and Units'},
                {u'id': u'5152cea8-829a-4aaf-bcc5-c58a416ecb66@7',
                 u'shortId': u'UVLOqIKa@7',
                 u'title': u'Accuracy, Precision, and Significant Figures'},
                {u'id': u'5838b105-41cd-4c3d-a957-3ac004a48af3@5',
                 u'shortId': u'WDixBUHN@5',
                 u'title': u'Approximation'},
                ],
         },
        {u'id': u'subcol',
         u'shortId': u'subcol',
         u'title': u"Further Applications of Newton's Laws: Friction, Drag, and Elasticity",
         u'contents': [
                {u'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                 u'shortId': u'JKLtEyKm@2',
                 u'title': u'Introduction: Further Applications of Newton\u2019s Laws'},
                {u'id': u'ea271306-f7f2-46ac-b2ec-1d80ff186a59@5',
                 u'shortId': u'6icTBvfy@5',
                 u'title': u'Friction'},
                {u'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                 u'shortId': u'JjRqQoS5@6',
                 u'title': u'Drag Forces'},
                {u'id': u'56f1c5c1-4014-450d-a477-2121e276beca@8',
                 u'shortId': u'VvHFwUAU@8',
                 u'title': u'Elasticity: Stress and Strain'},
                ],
         },
        {u'id': u'f6024d8a-1868-44c7-ab65-45419ef54881@3',
         u'shortId': u'9gJNihho@3',
         u'title': u'Atomic Masses'},
        {u'id': u'7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2',
         u'shortId': u'clA4axSn@2',
         u'title': u'Selected Radioactive Isotopes'},
        {u'id': u'c0a76659-c311-405f-9a99-15c71af39325@5',
         u'shortId': u'wKdmWcMR@5',
         u'title': u'Useful Inførmation'},
        {u'id': u'ae3e18de-638d-4738-b804-dc69cd4db3a3@5',
         u'shortId': u'rj4Y3mON@5',
         u'title': u'Glossary of Key Symbols and Notation'},
        ],
    }
COLLECTION_DERIVED_METADATA = {
    u'parent': {
        u'authors': [
            {u'surname': None, u'suffix': None,
             u'firstname': u'OpenStax College',
             u'title': None, u'id': u'OpenStaxCollege',
             u'fullname': u'OpenStax College',
             }],
        u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
        u'shortId': u'55_943-0',
        u'title': u'College Physics',
        u'version': u'7.1',
    },
    u'title': u'Derived Copy of College Physics'
}
MODULE_METADATA = {
    u'printStyle': None,
    u'roles': None,
    u'subjects': [u'Science and Technology'],
    u'abstract': None,
    u'authors': [{u'id': u'OpenStaxCollege',
                  u'fullname': u'OpenStax College',
                  u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  }],
    u'created': u'2013-07-31T19:07:24Z',
    u'doctype': u'',
    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca',
    u'shortId': u'VvHFwUAU',
    u'language': u'en',
    u'license': {
        u'code': u'by',
        u'version': u'4.0',
        u'name': u'Creative Commons Attribution License',
        u'url': u'http://creativecommons.org/licenses/by/4.0/',
        },
    u'licensors': [{u'surname': u'University',
                    u'firstname': u'Rice',
                    u'suffix': None,
                    u'title': None,
                    u'id': u'OSCRiceUniversity',
                    u'fullname': u'Rice University',
                    },
                   ],
    u'publishers': [{u'surname': None,
                     u'firstname': u'OpenStax College',
                     u'suffix': None,
                     u'title': None,
                     u'id': u'OpenStaxCollege',
                     u'fullname': u'OpenStax College',
                     },
                    {u'surname': u'Physics',
                     u'firstname': u'College',
                     u'suffix': None,
                     u'title': None,
                     u'id': u'cnxcap',
                     u'fullname': u'OSC Physics Maintainer',
                     }
                    ],
    u'title': u'Elasticity: Stress and Strain',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentTitle': None,
    u'parentVersion': '',
    u'parent': {
        u'authors': [],
        u'id': None,
        u'shortId': None,
        u'title': None,
        u'version': '',
        },
    u'revised': u'2013-07-31T19:07:24Z',
    u'stateid': 1,
    u'submitlog': u'Added more examples',
    u'submitter': {
        u'surname': None,
        u'firstname': u'OpenStax College',
        u'suffix': None,
        u'title': None,
        u'id': u'OpenStaxCollege',
        u'fullname': u'OpenStax College',
        },
    u'mediaType': u'application/vnd.org.cnx.module',
    u'version': u'8',
    u'googleAnalytics': None,
    u'buyLink': u'http://openstaxcollege.worksmartsuite.com/',
    u'legacy_id': u'm42081',
    u'legacy_version': u'1.8',
    u'history': [
        {
            u'version': u'8',
            u'revised': u'2013-07-31T19:07:24Z',
            u'changes': u'Added more examples',
            u'publisher': {
                u'surname': None,
                u'firstname': u'OpenStax College',
                u'suffix': None,
                u'title': None,
                u'id': u'OpenStaxCollege',
                u'fullname': u'OpenStax College',
                },
            },
        ],
    u'keywords': [
        u'bulk modulus', u'compression', u'deformation', u'force',
        u'Hooke\u2019s law', u'length', u'shear modulus', u'strain', u'stress',
        u'tension', u'Young\u2019s modulus', u'shear deformation',
        u'tensile strength',
        ],
    u'resources': [
        {u'media_type': u'text/xml',
         u'id': u'01b0137ec023558ef05c9a7ddc275cca055f3a65',
         u'filename': u'index_auto_generated.cnxml',
         },
        {u'media_type': u'image/jpg',
         u'id': u'03ab3d7bca387b142f226ea8b62e550b7a65a9e1',
         u'filename': u'Figure_06_03_09a.jpg',
         },
        {u'media_type': u'image/png',
         u'id': u'191d7161e775dacea2d0c2f81fa41f0eefd65eeb',
         u'filename': u'Figure_06_03_04a.jpg',
         },
        {u'media_type': u'image/jpg',
         u'id': u'3028d78f9f9d80f035bb4899cf8aa798d3befa79',
         u'filename': u'Figure_06_03_08a.jpg',
         },
        {u'media_type': u'image/jpg',
         u'id': u'4b832692d2a7318172d0c3d3a5986b1dc06aa2f5',
         u'filename': u'Figure_06_03_06a.jpg',
         },
        {u'media_type': u'image/png',
         u'id': u'8bebb2a5642cc453cbcca70f79fb2184e2976b60',
         u'filename': u'Figure_06_03_05_xa.jpg',
         },
        {u'media_type': u'image/jpg',
         u'id': u'95430b74a5ee9e09037c589feb0685ee226a06b8',
         u'filename': u'Figure_06_03_10a.jpg',
         },
        {u'media_type': u'text/xml',
         u'id': u'9ae3b93679f6a4db2b78454189841d8ade98e0e6',
         u'filename': u'index.cnxml',
         },
        {u'media_type': u'text/html',
         u'id': u'b0bc75065bf8567c3cffc8221d4e3e92cc7b359b',
         u'filename': u'index.cnxml.html',
         },
        {u'media_type': u'image/jpg',
         u'id': u'b1504837b73dc2756173109e32344f0147c2921a',
         u'filename': u'Figure_06_03_02a.jpg',
         },
        {u'media_type': u'image/jpg',
         u'id': u'b1cae2957bab746ebaf065bd43f567509a446c3b',
         u'filename': u'Figure_06_03_01a.jpg',
         },
        {u'media_type': u'image/jpg',
         u'id': u'ff325274bcfa3be254a6cf39f86985df7ddaf294',
         u'filename': u'Figure_06_03_03a.jpg',
         },
        ],
    }


SEARCH_RESULTS_FILEPATH = os.path.join(testing.DATA_DIRECTORY,
                                       'search_results.json')
with open(SEARCH_RESULTS_FILEPATH, 'r') as file:
    SEARCH_RESULTS = json.load(file)


@mock.patch('cnxarchive.views.fromtimestamp', mock.Mock(side_effect=testing.mocked_fromtimestamp))
class ViewsTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = 10000

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
        from .. import declare_api_routes
        declare_api_routes(config)

        # Set up type info
        from .. import declare_type_info
        declare_type_info(config)

        # Clear all cached searches
        import memcache
        mc_servers = self.settings['memcache-servers'].split()
        mc = memcache.Client(mc_servers, debug=0)
        mc.flush_all()
        mc.disconnect_all()

        # Patch database search so that it's possible to assert call counts
        # later
        from .. import cache
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


    @testing.db_connect
    def test_content_index_html(self, cursor):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        cursor.execute('DELETE FROM module_files')
        # Insert a file for version 4
        cursor.execute('''INSERT INTO files (file, media_type) VALUES
            (%s, 'text/html') RETURNING fileid''', [memoryview('Version 4')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename) VALUES
                       (%s, %s, 'index.cnxml.html')''',
                       [16, fileid])
        # Insert a file for version 5
        cursor.execute('''INSERT INTO files (file, media_type) VALUES
            (%s, 'text/html') RETURNING fileid''', [memoryview('Version 5')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename) VALUES
                       (%s, %s, 'index.cnxml.html')''',
                       [15, fileid])
        cursor.connection.commit()

        def get_content(version):
            # Build the request environment
            self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
            self.request.matched_route = mock.Mock()
            self.request.matched_route.name = 'content'

            # Call the view
            from ..views_folder.content import get_content
            content = get_content(self.request).json_body

            return content.pop('content')

        self.assertEqual(get_content(4), 'Version 4')
        self.assertEqual(get_content(5), 'Version 5')

    def test_content_collection_as_html(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        expected = u"""<html xmlns="http://www.w3.org/1999/xhtml">
  <body>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1.html">College Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:209deb1f-1a46-4369-9e0d-18674cf58a3e@7.html">Preface</a></li>\
<li><a>Introduction: The Nature of Science and Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:f3c9ab70-a916-4d8c-9256-42953287b4e9@3.html">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:d395b566-5fe3-4428-bcb2-19016e3aa3ce@4.html">Physics: An Introduction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:c8bdbabc-62b1-4a5f-b291-982ab25756d7@6.html">Physical Quantities and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:5152cea8-829a-4aaf-bcc5-c58a416ecb66@7.html">Accuracy, Precision, and Significant Figures</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:5838b105-41cd-4c3d-a957-3ac004a48af3@5.html">Approximation</a></li></ul></li>\
<li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2.html">Introduction: Further Applications of Newton’s Laws</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:ea271306-f7f2-46ac-b2ec-1d80ff186a59@5.html">Friction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:26346a42-84b9-48ad-9f6a-62303c16ad41@6.html">Drag Forces</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:56f1c5c1-4014-450d-a477-2121e276beca@8.html">Elasticity: Stress and Strain</a></li>\
</ul></li><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:f6024d8a-1868-44c7-ab65-45419ef54881@3.html">Atomic Masses</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2.html">Selected Radioactive Isotopes</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:c0a76659-c311-405f-9a99-15c71af39325@5.html">Useful Inførmation</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1:ae3e18de-638d-4738-b804-dc69cd4db3a3@5.html">Glossary of Key Symbols and Notation</a></li></ul></li></ul></body>\n</html>\n"""

        # Build the environment
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(uuid, version),
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-html'

        # Call the view
        from ..views_folder.content import get_content_html
        resp = get_content_html(self.request)

        # Check that the view returns the expected html
        p = HTMLParser.HTMLParser()
        self.assertMultiLineEqual(p.unescape(resp.body), expected)

    def test_content_module_as_html(self):
        uuid = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce'
        version = '4'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-html'

        # Call the view.
        from ..views_folder.content import get_content_html

        # Check that the view returns some html
        resp_body = get_content_html(self.request).body
        self.assertTrue(resp_body.startswith('<html'))

    def test_search(self):
        # Build the request
        self.request.params = {'q': '"college physics" sort:version'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(sorted(results.keys()), sorted(SEARCH_RESULTS.keys()))
        self.maxDiff = None
        for key in results:
            self.assertEqual(results[key], SEARCH_RESULTS[key])

    def test_search_filter_by_authorID(self):
        # Build the request
        self.request.params = {'q': '"college physics" authorID:cnxcap'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['query'], {
            u'sort': [],
            u'per_page': 20,
            u'page': 1,
            u'limits': [{u'tag': u'text', u'value': u'college physics'},
                        {u'tag': u'authorID', u'index': 0,
                         u'value': u'cnxcap'}],
            })

    def test_author_special_case_search(self):
        '''
        Test the search case where an additional database query is needed to
        return auxiliary author info when the first query returned no
        results.
        '''

        # Build the request
        import string
        sub = 'subject:"Arguing with Judge Judy: Popular ‘Logic’ on TV Judge Shows"'
        auth0 = 'authorID:cnxcap'
        auth1 = 'authorID:OpenStaxCollege'
        auth2 = 'authorID:DrBunsenHoneydew'
        fields = [sub, auth0, auth1, auth2]
        self.request.params = {'q': string.join(fields, ' ')}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 0)

        expected = [
            {u'surname': u'Physics',
             u'firstname': u'College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OSC Physics Maintainer',
             u'id': u'cnxcap',
             },
            {u'surname': None,
             u'firstname': u'OpenStax College',
             u'suffix': None,
             u'title': None,
             u'fullname': u'OpenStax College',
             u'id': u'OpenStaxCollege',
             },
            {u'fullname': None,
             u'id': u'DrBunsenHoneydew',
             },
            ]

        auxiliary_authors = results['results']['auxiliary']['authors']

        self.assertEqual(auxiliary_authors, expected)

        # check to see if auxilary authors list is referenced
        # by the correct indexs in results['query']['limits']
        # list
        for limit in results['query']['limits']:
            if limit['tag'] == 'authorID':
                self.assertIn('index', limit.keys())
                idx = limit['index']
                aux_info = expected[idx]
                self.assertEqual(limit['value'], aux_info['id'])

    def test_search_only_subject(self):
        # From the Content page, we have a list of subjects (tags),
        # they link to the search page like: /search?q=subject:"Arts"

        # Build the request
        self.request.params = {'q': 'subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [{u'tag': u'subject', u'value': u'Science and Technology'}],
            u'sort': []})
        self.assertEqual(results['results']['total'], 7)

    def test_search_w_html_title(self):
        # Build the request
        self.request.params = {'q': 'title:"Derived Copy of College Physics" type:book'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [
                {u'tag': u'title', u'value': u'Derived Copy of College Physics'},
                {u'tag': u'type', u'value': u'book'},
                ],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_with_subject(self):
        # Build the request
        self.request.params = {'q': 'title:"college physics" subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            u'per_page': 20,
            u'page': 1,
            u'limits': [
                {u'tag': u'title', u'value': u'college physics'},
                {u'tag': u'subject', u'value': 'Science and Technology'},
                ],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_highlight_abstract(self):
        # Build the request
        self.request.params = {'q': '"college physics"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(
            results['results']['items'][0]['summarySnippet'],
            'algebra-based, two-semester <b>college</b> <b>physics</b> book '
            'is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental '
            '<b>physics</b> concepts. This online, fully editable and '
            'customizable title includes learning objectives, concept '
            'questions, links to labs and simulations, and ample practice '
            'opportunities to solve traditional <b>physics</b> application '
            'problems. ')
        self.assertEqual(
            results['results']['items'][1]['summarySnippet'],
            'algebra-based, two-semester <b>college</b> <b>physics</b> book '
            'is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental '
            '<b>physics</b> concepts. This online, fully editable and '
            'customizable title includes learning objectives, concept '
            'questions, links to labs and simulations, and ample practice '
            'opportunities to solve traditional <b>physics</b> application '
            'problems. ')
        self.assertEqual(results['results']['items'][2]['summarySnippet'],
                         ' A number list:   one  two  three   ')

        # Test for no highlighting on specific field queries.
        self.request.params = {'q': 'title:"college physics"'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(
            results['results']['items'][0]['summarySnippet'],
            ' This introductory, algebra-based, two-semester college physics '
            'book is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental physics '
            'concepts. This online, fully editable and customizable title '
            'includes learning objectives, concept questions, links to labs '
            'and simulations, and ample practice opportunities to solve '
            'traditional')
        self.assertEqual(
            results['results']['items'][1]['summarySnippet'],
            ' This introductory, algebra-based, two-semester college physics '
            'book is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental physics '
            'concepts. This online, fully editable and customizable title '
            'includes learning objectives, concept questions, links to labs '
            'and simulations, and ample practice opportunities to solve '
            'traditional')

        self.assertEqual(results['results']['items'][2]['summarySnippet'],
                         ' A number list:   one  two  three   ')

    def test_search_no_params(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results, {
            u'query': {
                u'limits': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [],
                },
            })

    def test_search_whitespace(self):
        self.request.params = {'q': ' '}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results, json.dumps({
            u'query': {
                u'limits': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [],
                },
            }))

    def test_search_utf8(self):
        self.request.params = {'q': '"你好"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': u'你好'}],
                u'sort': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_punctuations(self):
        self.request.params = {'q': r":\.+'?"}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': ur":\.+'?"}],
                u'sort': [],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_unbalanced_quotes(self):
        self.request.params = {'q': r'"a phrase" "something else sort:pubDate author:"first last"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            u'query': {
                u'limits': [
                    {u'tag': u'text', u'value': u'a phrase'},
                    {u'tag': u'text', u'value': u'something else'},
                    {u'tag': u'author', u'value': 'first last'},
                    ],
                u'sort': [u'pubDate'],
                u'per_page': 20,
                u'page': 1,
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                    {u'tag': u'type',
                     u'values': [
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.collection'},
                         {u'count': 0,
                          u'value': u'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                u'auxiliary': {
                    u'authors': [],
                    u'types': [
                        {u'name': u'Book',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Page',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_type_page_or_module(self):
        # Test searching "page"

        # Build the request
        self.request.params = {'q': 'title:"college physics" type:page'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'page'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.module')

        # Test searching "module"

        # Build the request
        self.request.params = {'q': '"college physics" type:module'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'module'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.module')

    def test_search_type_book_or_collection(self):
        # Test searching "book"

        # Build the request
        self.request.params = {'q': 'title:physics type:book'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'book'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.collection')

        # Test searching "collection"

        # Build the request
        self.request.params = {'q': 'title:physics type:collection'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'collection'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.collection')

    def test_search_wo_cache(self):
        # Patch settings so caching is disabled
        settings = self.settings.copy()
        settings['memcache-servers'] = ''
        config_kwargs = dict(settings=settings, request=self.request)
        from ..views import search

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        def call_search_view():
            with pyramid_testing.testConfig(**config_kwargs):
                return search(self.request)

        results = call_search_view().json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 3)

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        results = call_search_view().json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 2)

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '3'}

        results = call_search_view().json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 0)

        # Made 4 requests, so should have called db search 4 times
        self.assertEqual(self.db_search_call_count, 3)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_pagination(self):
        # Test search results with pagination

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'sort': [],
            'limits': [{'tag': 'text', 'value': 'introduction'}],
            'per_page': 3,
            'page': 1,
            })
        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 3)
        self.assertEqual(
                results['results']['items'][0]['title'],
                'Introduction to Science and the Realm of Physics, '
                'Physical Quantities, and Units')
        self.assertEqual(results['results']['items'][1]['title'],
                         'Physics: An Introduction')
        self.assertEqual(
                results['results']['items'][2]['title'],
                u'Introduction: Further Applications of Newton’s Laws')
        pub_year = [limit['values'] for limit in results['results']['limits']
                    if limit['tag'] == 'pubYear'][0]
        self.assertEqual(pub_year, [{'value': '2013', 'count': 5}])

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'sort': [],
            'limits': [{'tag': 'text', 'value': 'introduction'}],
            'per_page': 3,
            'page': 2,
            })
        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 2)
        self.assertEqual(results['results']['items'][0]['title'],
                         'Preface to College Physics')
        self.assertEqual(results['results']['items'][1]['title'],
                         'Physical Quantities and Units')
        pub_year = [limit['values'] for limit in results['results']['limits']
                    if limit['tag'] == 'pubYear'][0]
        self.assertEqual(pub_year, [{'value': '2013', 'count': 5}])

        # Fetch next page
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '3'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'sort': [],
            'limits': [{'tag': 'text', 'value': 'introduction'}],
            'per_page': 3,
            'page': 3,
            })
        self.assertEqual(results['results']['total'], 5)
        self.assertEqual(len(results['results']['items']), 0)
        pub_year = [limit['values'] for limit in results['results']['limits']
                    if limit['tag'] == 'pubYear'][0]
        self.assertEqual(pub_year, [{'value': '2013', 'count': 5}])

        # Fetching all the pages should only query the
        # database once because the result should already
        # been cached in memcached
        self.assertEqual(self.db_search_call_count, 1)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_nocache(self):
        # Disable caching from url with nocache=True

        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Search again but with caching disabled
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'nocache': 'True'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_cache_expired(self):
        # Build the request
        self.request.params = {'q': 'introduction',
                               'per_page': '3'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Fetch next page (should use cache)
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 1)

        # Wait for cache to expire
        time.sleep(30)

        # Fetch the same page (cache expired)
        self.request.params = {'q': 'introduction',
                               'per_page': '3',
                               'page': '2'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_normal_cache(self):
        # Build the request
        self.request.params = {'q': '"college physics"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again after cache is expired
        time.sleep(20)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 3)
        self.assertEqual(self.db_search_call_count, 2)

    @unittest.skipUnless(testing.IS_MEMCACHE_ENABLED, "requires memcached")
    def test_search_w_long_cache(self):
        # Test searches which should be cached for longer

        # Build the request for subject search
        self.request.params = {'q': 'subject:"Science and Technology"'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'search'

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again (should use cache)
        time.sleep(20)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 1)

        # Search again after cache is expired
        time.sleep(15)
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 7)
        self.assertEqual(self.db_search_call_count, 2)

        def _remove_timestamps(messages):
            for message in messages:
                message.pop('starts')
                message.pop('ends')
            return messages
        self.assertEqual(expected_messages, _remove_timestamps(messages))

    def test_sitemap(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'sitemap'

        # Call the view
        from ..views import sitemap
        sitemap = sitemap(self.request).body
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'sitemap.xml')
        with open(expected_file, 'r') as file:
            self.assertMultiLineEqual(sitemap, file.read())
