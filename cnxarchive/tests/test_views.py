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
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    from unittest import mock
except ImportError:
    import mock

from pyramid import httpexceptions
from pyramid import testing as pyramid_testing

from ..utils import IdentHashShortId, IdentHashMissingVersion
from . import testing


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
        {u'filename': u'featured-cover.png',
         u'id': u'6214e8dcdf2824dbf830b4a0d77a3fa2f53608d2',
         u'media_type': u'image/png',
         },
        # FIXME This file probably shouldn't exist?
        {u'filename': u'collection.html',
         u'id': u'921dcf515d41c5a5cbe3c2163ed0f5db02ab3c83',
         u'media_type': u'text/xml',
         },
        {u'filename': u'collection.xml',
         u'id': u'921dcf515d41c5a5cbe3c2163ed0f5db02ab3c83',
         u'media_type': u'text/xml',
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

    def test_collection_content(self):
        # Test for retrieving a piece of content.
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(COLLECTION_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], COLLECTION_METADATA[key])
        self.maxDiff = 10000
        # Check the tree for accuracy.
        self.assertEqual(content_tree, COLLECTION_JSON_TREE)

    def test_derived_collection(self):
        # Test for retrieving a piece of content.
        uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        version = '1.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()),
                         sorted(COLLECTION_METADATA.keys()))
        for key in COLLECTION_DERIVED_METADATA['parent']:
            self.assertEqual(content['parent'][key],
                             COLLECTION_DERIVED_METADATA['parent'][key])

    def test_content_collated_collection(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        # Check the tree.
        self.assertEqual({
            u'id': u'{}@{}'.format(uuid, version),
            u'shortId': u'55_943-0@6.1',
            u'title': u'College Physics',
            u'contents': [
                {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                 u'shortId': u'IJ3rHxpG@7',
                 u'title': u'Preface'},
                {u'id': u'174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                 u'shortId': u'F0xAaSdD@1',
                 u'title': u'Collated page'},
                ],
            }, content['tree'])

    @testing.db_connect
    def _create_empty_subcollections(self, cursor):
        cursor.execute("""\
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9100, 91, 'Empty Subcollections', 1, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9200, 9100, 'empty 1', 1, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9300, 9100, 'empty 2', 2, true);
INSERT INTO trees (nodeid, parent_id, title, childorder, is_collated)
    VALUES (9400, 91, 'Empty Subcollection', 4, true);
""")

    def test_empty_subcollection_content(self):
        self._create_empty_subcollections()

        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'
        from ..utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        content = get_content(self.request).json_body

        content_tree = content.pop('tree')

        self.assertEqual(content_tree, {
            u'id': u'{}@{}'.format(uuid, version),
            u'shortId': u'{}@{}'.format(short_id, version),
            u'title': u'College Physics',
            u'contents': [
                {
                    u'id': u'subcol',
                    u'shortId': u'subcol',
                    u'title': u'Empty Subcollections',
                    u'contents': [
                        {
                            u'id': u'subcol',
                            u'shortId': u'subcol',
                            u'title': u'empty 1',
                            u'contents': [],
                            },
                        {
                            u'id': u'subcol',
                            u'shortId': u'subcol',
                            u'title': u'empty 2',
                            u'contents': [],
                            },

                        ],
                    },
                {
                    u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                    u'shortId': u'IJ3rHxpG@7',
                    u'title': u'Preface',
                    },
                {
                    u'id': u'174c4069-2743-42e9-adfe-4c7084f81fc5@1',
                    u'shortId': u'F0xAaSdD@1',
                    u'title': u'Collated page',
                    },
                {
                    u'id': u'subcol',
                    u'shortId': u'subcol',
                    u'title': u'Empty Subcollection',
                    u'contents': [],
                    },
                ],
            })

    def test_history_metadata(self):
        # Test for the history field in the metadata
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        content = get_content(self.request).json_body

        # History should only include displayed version and older versions
        self.assertEqual(content['history'], [{
            u'version': u'6.1',
            u'revised': u'2013-07-31T19:07:20Z',
            u'changes': u'Updated something',
            u'publisher': {
                u'surname': None,
                u'firstname': u'OpenStax College',
                u'suffix': None,
                u'title': None,
                u'id': u'OpenStaxCollege',
                u'fullname': u'OpenStax College',
                },
            }])

    def test_module_content(self):
        # Test for retreiving a module.
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ..views import get_content

        content = get_content(self.request).json_body

        # Remove the 'content' text from the content for separate testing.
        content_text = content.pop('content')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(MODULE_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], MODULE_METADATA[key],
                             u'content[{key}] = {v1} but MODULE_METADATA[{key}] = {v2}'.format(
                             key=key, v1=content[key], v2=MODULE_METADATA[key]))

        # Check the content is the html file.
        self.assertTrue(content_text.find('<html') >= 0)

    def test_content_composite_page_wo_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ..views import get_content

        # Composite modules cannot be retrieved outside of a collection
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_composite_page_in_wrong_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(uuid, version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ..views import get_content

        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_composite_page_in_book(self):
        # Test for retrieving a a composite module.
        uuid = '174c4069-2743-42e9-adfe-4c7084f81fc5'
        version = '1'
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(uuid, version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        from ..views import get_content

        content = get_content(self.request).json_body

        # Check the media type.
        self.assertEqual(
            'application/vnd.org.cnx.composite-module',
            content['mediaType'])

        # Check the content.
        self.assertEqual(
            '<html><body>test collated content</body></html>',
            content['content'])

    def test_content_without_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': uuid,
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_content(self.request)

    def test_content_shortid_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        version = 5
        from ..utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': "{}@{}".format(short_id, version)
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_shortid_no_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        from ..utils import CNXHash
        cnxhash = CNXHash(uuid)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': short_id
        }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_not_found(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': '98c44aed-056b-450a-81b0-61af87ee75af'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        self.assertRaises(IdentHashMissingVersion, get_content,
                          self.request)

    def test_content_not_found_w_invalid_uuid(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': 'notfound@1'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        self.assertRaises(IdentHashShortId, get_content,
                          self.request)

    def test_content_collated_page_inside_book(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '6.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(book_uuid, book_version),
            'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        self.assertEqual(
            '<html><body>Page content after collation</body></html>\n',
            content['content'])

    def test_content_uncollated_page(self):
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        # Build the request.
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(page_uuid, page_version),
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        self.assertNotEqual(
            '<html><body>Page content after collation</body></html>\n',
            content['content'])

    def test_content_page_inside_book_version_mismatch(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_uuid, book_version),
                'page_ident_hash': '{}@0'.format(page_uuid),
                'separator': ':',
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_page_inside_book_w_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_uuid, book_version),
                'page_ident_hash': '{}@{}'.format(page_uuid, page_version),
                'separator': ':',
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            get_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(
            cm.exception.headers['Location'],
            quote('/contents/{}@{}'.format(page_uuid, page_version)))

    def test_content_page_inside_book_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
            'ident_hash': book_uuid,
            'page_ident_hash': page_uuid,
            'separator': ':',
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_content(self.request)

    def test_content_page_inside_book_version_mismatch_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ..utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_shortid, book_version),
                'page_ident_hash': '{}@0'.format(page_shortid),
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_page_inside_book_w_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ..utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_shortid, book_version),
                'page_ident_hash': '{}@{}'.format(page_shortid, page_version),
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_content_page_inside_book_wo_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        from ..utils import CNXHash
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        # Build the request
        self.request.matchdict = {
            'ident_hash': book_shortid,
            'page_ident_hash': page_shortid,
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content'

        # Call the view
        from ..views import get_content
        with self.assertRaises(IdentHashShortId) as cm:
            get_content(self.request)

    def test_legacy_id_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, latest version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@5'.format(uuid)))

    def test_legacy_id_ver_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.5'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, latest version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@5'.format(uuid)))

    def test_legacy_id_old_ver_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@4'.format(uuid)))

    def test_legacy_bad_id_redirect(self):
        objid = 'foobar'

        # Build the request environment.
        self.request.matchdict = {'objid': objid}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPNotFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '404 Not Found')

    def test_legacy_id_old_ver_collection_context(self):
        book_uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        page_uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'
        colid = 'col15533'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.params = {'collection': '{}/latest'.format(colid)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(
            cm.exception.headers['Location'],
            quote('/contents/{}@1.1:{}'.format(book_uuid, page_uuid)))

    def test_legacy_id_old_ver_bad_collection_context(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid, 'objver': '1.4'}
        self.request.params = {'collection': 'col45555/latest'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the new url, old version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@4'.format(uuid)))

    def test_legacy_filename_redirect(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        objid = 'm42081'
        objver = '1.8'
        filename = 'Figure_06_03_10a.jpg'
        sha1 = '95430b74a5ee9e09037c589feb0685ee226a06b8'

        # Build the request environment.
        self.request.matchdict = {'objid': objid,
                                  'objver': objver,
                                  'filename': filename}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view redirects to the resources url
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            redirect_legacy_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/resources/{}/{}'.format(sha1, filename)))

    def test_legacy_no_such_filename_redirect(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        objid = 'm42081'
        objver = '1.8'
        filename = 'nothere.png'

        # Build the request environment.
        self.request.matchdict = {'objid': objid,
                                  'objver': objver,
                                  'filename': filename}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'legacy-redirect-w-version'

        # Call the view.
        from ..views import redirect_legacy_content

        # Check that the view 404s
        self.assertRaises(httpexceptions.HTTPNotFound,
                          redirect_legacy_content, self.request)

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
            from ..views import get_content
            content = get_content(self.request).json_body

            return content.pop('content')

        self.assertEqual(get_content(4), 'Version 4')
        self.assertEqual(get_content(5), 'Version 5')

    def test_content_collection_as_html(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        expected = u"""<html xmlns="http://www.w3.org/1999/xhtml">
  <body>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1.html">College Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A209deb1f-1a46-4369-9e0d-18674cf58a3e%407.html">Preface</a></li>\
<li><a>Introduction: The Nature of Science and Physics</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Af3c9ab70-a916-4d8c-9256-42953287b4e9%403.html">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Ad395b566-5fe3-4428-bcb2-19016e3aa3ce%404.html">Physics: An Introduction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Ac8bdbabc-62b1-4a5f-b291-982ab25756d7%406.html">Physical Quantities and Units</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A5152cea8-829a-4aaf-bcc5-c58a416ecb66%407.html">Accuracy, Precision, and Significant Figures</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A5838b105-41cd-4c3d-a957-3ac004a48af3%405.html">Approximation</a></li></ul></li>\
<li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d%402.html">Introduction: Further Applications of Newton’s Laws</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Aea271306-f7f2-46ac-b2ec-1d80ff186a59%405.html">Friction</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A26346a42-84b9-48ad-9f6a-62303c16ad41%406.html">Drag Forces</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A56f1c5c1-4014-450d-a477-2121e276beca%408.html">Elasticity: Stress and Strain</a></li>\
</ul></li><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Af6024d8a-1868-44c7-ab65-45419ef54881%403.html">Atomic Masses</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3A7250386b-14a7-41a2-b8bf-9e9ab872f0dc%402.html">Selected Radioactive Isotopes</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Ac0a76659-c311-405f-9a99-15c71af39325%405.html">Useful Inførmation</a></li>\
<li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1%3Aae3e18de-638d-4738-b804-dc69cd4db3a3%405.html">Glossary of Key Symbols and Notation</a></li></ul></li></ul></body>\n</html>\n"""

        # Build the environment
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(uuid, version),
            }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-html'

        # Call the view
        from ..views import get_content_html
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
        from ..views import get_content_html

        # Check that the view returns some html
        resp_body = get_content_html(self.request).body
        self.assertTrue(resp_body.startswith('<html'))

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        hash = '075500ad9f71890a85fe3f7a4137ac08e2b7907c'

        # Build the request.
        self.request.matchdict = {'hash': hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'resource'

        # Call the view.
        from ..views import get_resource
        resource = get_resource(self.request).body

        expected_bits = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xfe\x00\x00\x00\x93\x08\x06\x00\x00\x00\xf6\x90\x1d\x14'
        # Check the response body.
        self.assertEqual(bytes(resource)[:len(expected_bits)],
                         expected_bits)

        self.assertEqual(self.request.response.content_type, 'image/png')

    def test_resources_404(self):
        hash = 'invalid-hash'

        # Build the request
        self.request.matchdict = {'hash': hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'resource'

        # Call the view
        from ..views import get_resource
        self.assertRaises(httpexceptions.HTTPNotFound, get_resource,
                          self.request)

    def test_exports(self):
        # Test for the retrieval of exports (e.g. pdf files).
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        filename = "{}@{}.{}".format(id, version, type)

        # Build the request.
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': type,
                                  }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ..views import get_export
        export = get_export(self.request).body

        self.assertEqual(self.request.response.content_disposition,
                         "attached; filename=college-physics-{}.pdf"
                         .format(version))
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports',
                                     filename)
        with open(expected_file, 'r') as file:
            self.assertEqual(export, file.read())

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}@{}.pdf'.format(id, version)
        self.request.matchdict = {'ident_hash': ident_hash,
                                  'type': 'pdf'
                                  }

        export = get_export(self.request).body
        self.assertEqual(
            self.request.response.content_disposition,
            "attached; filename=elasticity-stress-and-strain-{}.pdf"
            .format(version))

        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports2',
                                     filename)
        with open(expected_file, 'r') as file:
            self.assertEqual(export, file.read())

    def test_exports_type_not_supported(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '56f1c5c1-4014-450d-a477-2121e276beca@8',
                'type': 'txt'
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_404(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_without_version(self):
        id = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request
        self.request.matchdict = {'ident_hash': id, 'type': 'pdf'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'export'

        from ..views import get_export
        with self.assertRaises(IdentHashMissingVersion) as cm:
            get_export(self.request)

    def test_get_extra_no_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'downloads': [{
                u'created': None,
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'college-physics-6.1.pdf',
                u'format': u'PDF',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.pdf/college-physics-6.1.pdf'),
                u'size': 0,
                u'state': u'missing'},
               {
                u'created': None,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'college-physics-6.1.epub',
                u'format': u'EPUB',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.epub/college-physics-6.1.epub'),
                u'size': 0,
                u'state': u'missing'},
               {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'college-physics-6.1.zip',
                u'format': u'Offline ZIP',
                u'path': quote(u'/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.zip/college-physics-6.1.zip'),
                u'size': 0,
                u'state': u'missing'}],
            u'isLatest': False,
            u'canPublish': [
                u'OpenStaxCollege',
                u'cnxcap',
                ],
            })

    def test_get_extra_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'PDF',
                u'size': 28,
                u'state': u'good',
                u'filename': u'college-physics-{}.pdf'.format(version),
                u'details': u'PDF file, for viewing content offline and printing.',
                u'path': quote(u'/exports/{}@{}.pdf/college-physics-{}.pdf'.format(
                    id, version, version)),
                },
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'EPUB',
                u'size': 13,
                u'state': u'good',
                u'filename': u'college-physics-{}.epub'.format(version),
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'path': quote(u'/exports/{}@{}.epub/college-physics-{}.epub'.format(
                    id, version, version)),
                },
            {
                u'created': u'2015-03-04T10:03:29-08:00',
                u'format': u'Offline ZIP',
                u'size': 11,
                u'state': u'good',
                u'filename': u'college-physics-{}.zip'.format(version),
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'path': quote(u'/exports/{}@{}.zip/college-physics-{}.zip'.format(
                    id, version, version)),
                },
            ])

    def test_extra_downloads_with_legacy_filenames(self):
        # Tests for finding legacy filenames after a module is published from
        # the legacy site
        id = '209deb1f-1a46-4369-9e0d-18674cf58a3e'  # m42955
        version = '7'  # legacy_version: 1.7
        requested_ident_hash = '{}@{}'.format(id, version)

        # Remove the generated files after the test
        def remove_generated_files():
            file_glob = glob.glob('{}/exports2/{}@{}.*'.format(testing.DATA_DIRECTORY,
                                                               id, version))
            for f in file_glob:
                os.unlink(f)
        self.addCleanup(remove_generated_files)

        # Build the request
        self.request.matchdict = {'ident_hash': requested_ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                u'path': quote(u'/exports/{}@{}.pdf/preface-to-college-physics-7.pdf'
                               .format(id, version)),
                u'format': u'PDF',
                u'created': u'2015-03-04T10:03:29-08:00',
                u'state': u'good',
                u'size': 15,
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'preface-to-college-physics-7.pdf',
                },
            {
                u'path': quote(u'/exports/{}@{}.epub/preface-to-college-physics-7.epub'
                               .format(id, version)),
                u'format': u'EPUB',
                u'created': u'2015-03-04T10:03:29-08:00',
                u'state': u'good',
                u'size': 16,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'preface-to-college-physics-7.epub',
                },
            {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'preface-to-college-physics-7.zip',
                u'format': u'Offline ZIP',
                u'path': quote(u'/exports/209deb1f-1a46-4369-9e0d-18674cf58a3e@7.zip/preface-to-college-physics-7.zip'),
                u'size': 0,
                u'state': u'missing'}
            ])

    def test_extra_latest(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['isLatest'], True)

        version = '6.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['isLatest'], False)

    def test_extra_wo_version(self):
        # Request the extras for a document, but without specifying
        #   the version. The expectation is that this will redirect to the
        #   latest version.
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        requested_ident_hash = id
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': requested_ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ..views import get_extra
        with self.assertRaises(IdentHashMissingVersion) as raiser:
            get_extra(self.request)

    def test_extra_shortid(self):
        # Request the extras for a document with a shortid and
        #   version. The expectation is that this will redirect to the
        #   fullid (uuid@version)

        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        from ..utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()
        version = '7.1'
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {
            'ident_hash': "{}@{}".format(short_id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ..views import get_extra
        with self.assertRaises(IdentHashShortId) as raiser:
            get_extra(self.request)

    def test_extra_shortid_wo_version(self):
        # Request the extras for a document with a shortid and no
        #   version. The expectation is that this will redirect to the
        #   fullid (uuid@version)

        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ..utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': short_id}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ..views import get_extra
        with self.assertRaises(IdentHashShortId) as raiser:
            get_extra(self.request)

    def test_extra_w_utf8_characters(self):
        id = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = '5'
        ident_hash = '{}@{}'.format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': ident_hash}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        # Call the target
        from ..views import get_extra
        output = get_extra(self.request).json_body
        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'canPublish': [
                u'OpenStaxCollege',
                u'cnxcap',
                ],
            u'isLatest': True,
            u'downloads': [{
                u'created': u'2015-03-04T10:03:29-08:00',
                u'path': quote('/exports/{}@{}.pdf/useful-inførmation-5.pdf'
                               .format(id, version)),
                u'format': u'PDF',
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'useful-inførmation-5.pdf',
                u'size': 0,
                u'state': u'good'},
                {
                u'created': None,
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'useful-inf\xf8rmation-5.epub',
                u'format': u'EPUB',
                u'path': quote('/exports/{}@{}.epub/useful-inførmation-5.epub'
                               .format(id, version)),
                u'size': 0,
                u'state': u'missing'},
                {
                u'created': None,
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'filename': u'useful-inf\xf8rmation-5.zip',
                u'format': u'Offline ZIP',
                u'path': quote('/exports/{}@{}.zip/useful-inførmation-5.zip'
                               .format(id, version)),
                u'size': 0,
                u'state': u'missing'}],
            })

    def test_extra_not_found(self):
        # Test version not found
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'content-extras'

        from ..views import get_extra
        self.assertRaises(httpexceptions.HTTPNotFound, get_extra,
                          self.request)

        # Test id not found
        id = 'c694e5cc-47bd-41a4-b319-030647d93440'
        version = '1.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        self.assertRaises(httpexceptions.HTTPNotFound, get_extra,
                          self.request)

    def test_in_book_search_wo_version(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': id}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ..views import in_book_search
        with self.assertRaises(IdentHashMissingVersion) as cm:
            in_book_search(self.request)

    def test_in_book_search_shortid(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ..utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {'ident_hash':
                                  '{}@{}'.format(short_id, version)}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ..views import in_book_search
        with self.assertRaises(IdentHashShortId) as cm:
            in_book_search(self.request)

    def test_in_book_search_short_id_wo_version(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        from ..utils import CNXHash
        cnxhash = CNXHash(id)
        short_id = cnxhash.get_shortid()

        # Build the request environment.
        self.request.matchdict = {'ident_hash': short_id}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        # Call the view.
        from ..views import in_book_search
        with self.assertRaises(IdentHashShortId) as cm:
            in_book_search(self.request)

    def test_in_book_search(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}
        # search query param
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search'

        from ..views import in_book_search
        results = in_book_search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        IN_BOOK_SEARCH_RESULT = {
            u'results': {
                u'items': [{
                    u'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                    u'matches': u'3',
                    u'rank': u'0.05',
                    u'snippet': u'have in mind the forces of friction, '
                                u'<span class="q-match">air</span> or '
                                u'<span class="q-match">liquid</span> '
                                u'<span class="q-match">drag</span>, '
                                u'and deformation',
                    u'title': u'Introduction: Further Applications of '
                              u'Newton\u2019s Laws'}, {
                    u'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                    u'matches': u'77',
                    u'rank': u'0.00424134',
                    u'snippet': u'absence of <span '
                                u'class="q-match">air</span> <span '
                                u'class="q-match">drag</span> (b) with '
                                u'<span class="q-match">air</span> <span '
                                u'class="q-match">drag</span>. Take the '
                                u'size across of the drop',
                    u'title': u'<span class="q-match">Drag</span> Forces'}, {
                    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca@8',
                    u'matches': u'13',
                    u'rank': u'2.59875e-05',
                    u'snippet': u'compress gases and extremely difficult '
                                u'to compress <span '
                                u'class="q-match">liquids</span> and '
                                u'solids. For example, <span '
                                u'class="q-match">air</span> in a wine '
                                u'bottle is compressed when',
                    u'title': u'Elasticity: Stress and Strain'}],
                u'query': {u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
                           u'search_term': u'air or liquid drag'},
                u'total': 3}}

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results, IN_BOOK_SEARCH_RESULT)

    def test_in_book_search_highlighted_results_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_version = '8'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': book_uuid,
                                  'page_ident_hash': page_uuid}
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search-page'

        # Call the view.
        from ..views import in_book_search_highlighted_results

        with self.assertRaises(IdentHashMissingVersion) as cm:
            in_book_search_highlighted_results(self.request)

    def test_in_book_search_highlighted_results(self):
        collection_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        collection_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_version = '8'

        # build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(collection_uuid, collection_version),
                                  'page_ident_hash': '{}@{}'.format(page_uuid, page_version)}
        # search query param
        self.request.params = {'q': 'air or liquid drag'}
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'in-book-search-page'

        from ..views import in_book_search_highlighted_results
        results = in_book_search_highlighted_results(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        title = results['results']['items'][0]['title']
        id = results['results']['items'][0]['id']
        content = results['results']['items'][0]['html']

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual('Elasticity: Stress and Strain', title)
        self.assertEqual('56f1c5c1-4014-450d-a477-2121e276beca@8', id)
        self.assertEqual("<mtext class=\"q-match\">air</mtext>" in content,
                         True)

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

    @testing.db_connect
    def test_extras(self, cursor):
        # Setup a few service state messages.
        cursor.execute("""\
INSERT INTO service_state_messages
  (service_state_id, starts, ends, priority, message)
VALUES
  (1, CURRENT_TIMESTAMP + INTERVAL '3 hours',
   CURRENT_TIMESTAMP + INTERVAL '24 hours',
   NULL, NULL),
  (2, DEFAULT, DEFAULT, 8,
   'We have free books at free prices! Don''t miss out!'),
  (2, CURRENT_TIMESTAMP - INTERVAL '24 hours',
   CURRENT_TIMESTAMP - INTERVAL '2 hours',
   1, 'should not show up in the results.')""")
        cursor.connection.commit()

        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'extras'

        # Call the view
        from ..views import extras
        metadata = extras(self.request).json_body
        messages = metadata.pop('messages')
        self.assertEqual(metadata, {
            u'subjects': [{u'id': 1, u'name': u'Arts',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 2, u'name': u'Business',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 3, u'name': u'Humanities',
                           u'count': {u'module': 0, u'collection': 0},
                           },
                          {u'id': 4, u'name': u'Mathematics and Statistics',
                           u'count': {u'module': 7, u'collection': 1},
                           },
                          {u'id': 5, u'name': u'Science and Technology',
                           u'count': {u'module': 6, u'collection': 1},
                           },
                          {u'id': 6, u'name': u'Social Sciences',
                           u'count': {u'module': 0, u'collection': 0},
                           }],
            u'featuredLinks': [{
                u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
                u'title': u'College Physics',
                u'version': u'7.1',
                u'legacy_id': u'col11406',
                u'legacy_version': u'1.7',
                u'resourcePath': u'/resources/6214e8dcdf2824dbf830b4a0d77a3fa2f53608d2',
                u'type': u'OpenStax Featured',
                u'abstract': u"""<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" \
xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">\
This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. \
This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics \
application problems.</div>""",
                }],
            u'languages_and_count': [[u'da', 1], [u'en', 17]],
            u'licenses': [{u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nd',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs License',
                           u'url': u'http://creativecommons.org/licenses/by-nd/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nd-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nd-nc/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nc/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by-sa',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-sa/1.0',
                           u'version': u'1.0'},
                          {u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/2.0/',
                           u'version': u'2.0'},
                          {u'code': u'by-nd',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs License',
                           u'url': u'http://creativecommons.org/licenses/by-nd/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-nd-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NoDerivs-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nd-nc/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-nc',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-NonCommercial License',
                           u'url': u'http://creativecommons.org/licenses/by-nc/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by-sa',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-sa/2.0',
                           u'version': u'2.0'},
                          {u'code': u'by',
                           u'isValidForPublication': False,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/3.0/',
                           u'version': u'3.0'},
                          {u'code': u'by',
                           u'isValidForPublication': True,
                           u'name': u'Creative Commons Attribution License',
                           u'url': u'http://creativecommons.org/licenses/by/4.0/',
                           u'version': u'4.0'},
                          {u'code': u'by-nc-sa',
                           u'isValidForPublication': True,
                           u'name': u'Creative Commons Attribution-NonCommercial-ShareAlike License',
                           u'url': u'http://creativecommons.org/licenses/by-nc-sa/4.0/',
                           u'version': u'4.0'}],
            })
        expected_messages = [
            {u'message': u'This site is scheduled to be down for maintaince, please excuse the interuption. Thank you.',
             u'name': u'Maintenance',
             u'priority': 1},
            {u'message': u"We have free books at free prices! Don't miss out!",
             u'name': u'Notice',
             u'priority': 8}
            ]

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

    def test_robots(self):
        self.request.matched_route = mock.Mock()
        self.request.matched_route.name = 'robots'

        # Call the view
        mocked_time = datetime.datetime(2015, 3, 4, 18, 3, 29)
        with mock.patch('cnxarchive.views.datetime') as mock_datetime:
            def patched_now_side_effect(timezone):
                return timezone.localize(mocked_time)
            mock_datetime.now.side_effect = patched_now_side_effect
            from ..views import robots
            robots = robots(self.request).body

        # Check the headers
        resp = self.request.response
        self.assertEqual(resp.content_type, 'text/plain')
        self.assertEqual(
            str(resp.cache_control), 'max-age=36000, must-revalidate')
        self.assertEqual(resp.headers['Last-Modified'],
                         'Wed, 04 Mar 2015 18:03:29 GMT')
        self.assertEqual(resp.headers['Expires'],
                         'Mon, 09 Mar 2015 18:03:29 GMT')

        # Check robots.txt content
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'robots.txt')
        with open(expected_file, 'r') as f:
            self.assertMultiLineEqual(robots, f.read())
