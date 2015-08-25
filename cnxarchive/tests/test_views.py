# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import os
import datetime
import glob
try:
    import html  # python 3
except ImportError:
    import HTMLParser  # python 2
import time
import json
import unittest
try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote

try:
    from unittest import mock
except ImportError:
    import mock

import psycopg2
from pyramid import httpexceptions
from pyramid import testing as pyramid_testing
from pyramid.request import Request
from pyramid.threadlocal import get_current_registry

from . import testing
from .. import IS_PY2


COLLECTION_METADATA = {
    'roles': None,
    'subjects': ['Mathematics and Statistics', 'Science and Technology', 'OpenStax Featured'],
    'abstract': '<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" '
                'xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">'
                'This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, '
                'fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample '
                'practice opportunities to solve traditional physics application problems.</div>',
    'authors': [{'id': 'OpenStaxCollege',
                 'fullname': 'OpenStax College',
                 'surname': None, 'suffix': None,
                 'firstname': 'OpenStax College', 'title': None,
                 }],
    'created': '2013-07-31T19:07:20Z',
    'doctype': '',
    'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    'language': 'en',
    'license': {
        'code': 'by',
        'version': '4.0',
        'name': 'Creative Commons Attribution License',
        'url': 'http://creativecommons.org/licenses/by/4.0/',
        },
    'licensors': [{'surname': 'University',
                   'firstname': 'Rice',
                   'suffix': None,
                   'title': None,
                   'id': 'OSCRiceUniversity',
                   'fullname': 'Rice University',
                   },
                  ],
    'publishers': [{'surname': None,
                    'firstname': 'OpenStax College',
                    'suffix': None,
                    'title': None,
                    'id': 'OpenStaxCollege',
                    'fullname': 'OpenStax College',
                    },
                   {'surname': 'Physics',
                    'firstname': 'College',
                    'suffix': None,
                    'title': None,
                    'id': 'cnxcap',
                    'fullname': 'OSC Physics Maintainer',
                    }
                   ],
    'title': 'College Physics',
    'parentAuthors': [],
    'parentId': None,
    'parentTitle': None,
    'parentVersion': '',
    'parent': {
        'authors': [],
        'id': None,
        'title': None,
        'version': '',
        },
    'revised': '2013-08-31T19:07:20Z',
    'stateid': None,
    'submitlog': 'New version 1.7',
    'submitter': {
        'surname': None,
        'firstname': 'OpenStax College',
        'suffix': None,
        'title': None,
        'id': 'OpenStaxCollege',
        'fullname': 'OpenStax College',
        },
    'mediaType': 'application/vnd.org.cnx.collection',
    'version': '7.1',
    'printStyle': None,
    'googleAnalytics': 'UA-XXXXX-Y',
    'buyLink': None,
    'legacy_id': 'col11406',
    'legacy_version': '1.7',
    'history': [
        {
            'version': '7.1',
            'revised': '2013-08-31T19:07:20Z',
            'changes': 'New version 1.7',
            'publisher': {
                'surname': None,
                'firstname': 'OpenStax College',
                'suffix': None,
                'title': None,
                'id': 'OpenStaxCollege',
                'fullname': 'OpenStax College',
                },
            },
        {
            'version': '6.1',
            'revised': '2013-07-31T19:07:20Z',
            'changes': 'Updated something',
            'publisher': {
                'surname': None,
                'firstname': 'OpenStax College',
                'suffix': None,
                'title': None,
                'id': 'OpenStaxCollege',
                'fullname': 'OpenStax College',
                },
            },
        ],
    'keywords': [
        'college physics', 'physics', 'friction', 'ac circuits',
        'atomic physics', 'bioelectricity',
        'biological and medical applications', 'circuits',
        'collisions', 'dc instruments', 'drag', 'elasticity',
        'electric charge and electric field', 'electric current',
        'electric potential', 'electrical technologies',
        'electromagnetic induction', 'electromagnetic waves', 'energy',
        'fluid dynamics', 'fluid statics', 'forces', 'frontiers of physics',
        'gas laws', 'geometric optics', 'heat and transfer methods',
        'kinematics', 'kinetic theory', 'linear momentum', 'magnetism',
        'medical applications of nuclear physics',
        'Newton\u2019s Laws of Motion', 'Ohm\u2019s Law',
        'oscillatory motion and waves', 'particle physics',
        'physics of hearing', 'quantum physics',
        'radioactivity and nuclear physics', 'resistance',
        'rotational motion and angular momentum', 'special relativity',
        'statics and torque', 'temperature', 'thermodynamics',
        'uniform circular motion and gravitation',
        'vision and optical instruments', 'wave optics', 'work',
        ],
    }
COLLECTION_JSON_TREE = {
    'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
    'title': 'College Physics',
    'contents': [
        {'id': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
         'title': 'Preface'},
        {'id': 'subcol',
         'title': 'Introduction: The Nature of Science and Physics',
         'contents': [
                {'id': 'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
                 'title': 'Introduction to Science and the Realm of Physics, Physical Quantities, and Units'},
                {'id': 'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
                 'title': 'Physics: An Introduction'},
                {'id': 'c8bdbabc-62b1-4a5f-b291-982ab25756d7@6',
                 'title': 'Physical Quantities and Units'},
                {'id': '5152cea8-829a-4aaf-bcc5-c58a416ecb66@7',
                 'title': 'Accuracy, Precision, and Significant Figures'},
                {'id': '5838b105-41cd-4c3d-a957-3ac004a48af3@5',
                 'title': 'Approximation'},
                ],
         },
        {'id': 'subcol',
         'title': "Further Applications of Newton's Laws: Friction, Drag, and Elasticity",
         'contents': [
                {'id': '24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                 'title': 'Introduction: Further Applications of Newton\u2019s Laws'},
                {'id': 'ea271306-f7f2-46ac-b2ec-1d80ff186a59@5',
                 'title': 'Friction'},
                {'id': '26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                 'title': 'Drag Forces'},
                {'id': '56f1c5c1-4014-450d-a477-2121e276beca@8',
                 'title': 'Elasticity: Stress and Strain'},
                ],
         },
        {'id': 'f6024d8a-1868-44c7-ab65-45419ef54881@3',
         'title': 'Atomic Masses'},
        {'id': '7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2',
         'title': 'Selected Radioactive Isotopes'},
        {'id': 'c0a76659-c311-405f-9a99-15c71af39325@5',
         'title': 'Useful Inførmation'},
        {'id': 'ae3e18de-638d-4738-b804-dc69cd4db3a3@5',
         'title': 'Glossary of Key Symbols and Notation'},
        ],
    }
COLLECTION_DERIVED_METADATA = {
    'parent': {
        'authors': [
            {'surname': None, 'suffix': None,
             'firstname': 'OpenStax College',
             'title': None, 'id': 'OpenStaxCollege',
             'fullname': 'OpenStax College',
             }],
        'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
        'title': 'College Physics',
        'version': '7.1',
    },
    'title': 'Derived Copy of College Physics'
}
MODULE_METADATA = {
    'printStyle': None,
    'roles': None,
    'subjects': ['Science and Technology'],
    'abstract': None,
    'authors': [{'id': 'OpenStaxCollege',
                 'fullname': 'OpenStax College',
                 'surname': None, 'suffix': None,
                 'firstname': 'OpenStax College', 'title': None,
                 }],
    'created': '2013-07-31T19:07:24Z',
    'doctype': '',
    'id': '56f1c5c1-4014-450d-a477-2121e276beca',
    'language': 'en',
    'license': {
        'code': 'by',
        'version': '4.0',
        'name': 'Creative Commons Attribution License',
        'url': 'http://creativecommons.org/licenses/by/4.0/',
        },
    'licensors': [{'surname': 'University',
                   'firstname': 'Rice',
                   'suffix': None,
                   'title': None,
                   'id': 'OSCRiceUniversity',
                   'fullname': 'Rice University',
                   },
                  ],
    'publishers': [{'surname': None,
                    'firstname': 'OpenStax College',
                    'suffix': None,
                    'title': None,
                    'id': 'OpenStaxCollege',
                    'fullname': 'OpenStax College',
                    },
                   {'surname': 'Physics',
                    'firstname': 'College',
                    'suffix': None,
                    'title': None,
                    'id': 'cnxcap',
                    'fullname': 'OSC Physics Maintainer',
                    }
                   ],
    'title': 'Elasticity: Stress and Strain',
    'parentAuthors': [],
    'parentId': None,
    'parentTitle': None,
    'parentVersion': '',
    'parent': {
        'authors': [],
        'id': None,
        'title': None,
        'version': '',
        },
    'revised': '2013-07-31T19:07:24Z',
    'stateid': None,
    'submitlog': 'Added more examples',
    'submitter': {
        'surname': None,
        'firstname': 'OpenStax College',
        'suffix': None,
        'title': None,
        'id': 'OpenStaxCollege',
        'fullname': 'OpenStax College',
        },
    'mediaType': 'application/vnd.org.cnx.module',
    'version': '8',
    'googleAnalytics': None,
    'buyLink': 'http://openstaxcollege.worksmartsuite.com/',
    'legacy_id': 'm42081',
    'legacy_version': '1.8',
    'history': [
        {
            'version': '8',
            'revised': '2013-07-31T19:07:24Z',
            'changes': 'Added more examples',
            'publisher': {
                'surname': None,
                'firstname': 'OpenStax College',
                'suffix': None,
                'title': None,
                'id': 'OpenStaxCollege',
                'fullname': 'OpenStax College',
                },
            },
        ],
    'keywords': [
        'bulk modulus', 'compression', 'deformation', 'force',
        'Hooke\u2019s law', 'length', 'shear modulus', 'strain', 'stress',
        'tension', 'Young\u2019s modulus', 'shear deformation',
        'tensile strength',
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

    @testing.db_connect
    def _create_empty_subcollections(self, cursor):
        cursor.execute("INSERT INTO trees VALUES (91, 53, NULL, 'Empty Subcollections', 1)")
        cursor.execute("INSERT INTO trees VALUES (92, 91, NULL, 'empty 1', 1)")
        cursor.execute("INSERT INTO trees VALUES (93, 91, NULL, 'empty 2', 2)")
        cursor.execute("INSERT INTO trees VALUES (94, 53, NULL, 'Empty Subcollection', 3)")

    def test_empty_subcollection_content(self):
        self._create_empty_subcollections()

        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}

        # Call the view
        from ..views import get_content
        content = get_content(self.request).json_body

        content_tree = content.pop('tree')

        self.assertEqual(content_tree, {
            'id': '{}@{}'.format(uuid, version),
            'title': 'College Physics',
            'contents': [
                {
                    'id': 'subcol',
                    'title': 'Empty Subcollections',
                    'contents': [
                        {
                            'id': 'subcol',
                            'title': 'empty 1',
                            'contents': [],
                            },
                        {
                            'id': 'subcol',
                            'title': 'empty 2',
                            'contents': [],
                            },

                        ],
                    },
                {
                    'id': '209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                    'title': 'Preface',
                    },
                {
                    'id': 'subcol',
                    'title': 'Empty Subcollection',
                    'contents': [],
                    },
                ],
            })

    def test_history_metadata(self):
        # Test for the history field in the metadata
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request environment
        self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}

        # Call the view
        from ..views import get_content
        content = get_content(self.request).json_body

        # History should only include displayed version and older versions
        self.assertEqual(content['history'], [{
            'version': '6.1',
            'revised': '2013-07-31T19:07:20Z',
            'changes': 'Updated something',
            'publisher': {
                'surname': None,
                'firstname': 'OpenStax College',
                'suffix': None,
                'title': None,
                'id': 'OpenStaxCollege',
                'fullname': 'OpenStax College',
                },
            }])

    def test_module_content(self):
        # Test for retreiving a module.
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}

        # Call the view.
        from ..views import get_content
        content = get_content(self.request).json_body

        # Remove the 'content' text from the content for separate testing.
        content_text = content.pop('content')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(MODULE_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], MODULE_METADATA[key],
                             'content[{key}] = {v1} but MODULE_METADATA[{key}] = {v2}'.format(
                             key=key, v1=content[key], v2=MODULE_METADATA[key]))

        # Check the content is the html file.
        self.assertTrue(content_text.find('<html') >= 0)

    def test_content_without_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request environment.
        self.request.matchdict = {
            'ident_hash': uuid,
            }

        # Call the view.
        from ..views import get_content

        # Check that the view redirects to the latest version
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            get_content(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/contents/{}@5.json'.format(uuid)))

    def test_content_not_found(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': '98c44aed-056b-450a-81b0-61af87ee75af'}

        # Call the view
        from ..views import get_content
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_not_found_w_invalid_uuid(self):
        # Build the request environment
        self.request.matchdict = {'ident_hash': 'notfound@1'}

        # Call the view
        from ..views import get_content
        self.assertRaises(httpexceptions.HTTPNotFound, get_content,
                          self.request)

    def test_content_page_inside_book_version_mismatch(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        # Build the request
        self.request.matchdict = {
                'ident_hash': '{}@{}'.format(book_uuid, book_version),
                'page_ident_hash': '{}@0'.format(page_uuid),
                }

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
                }

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
            }

        # Call the view
        from ..views import get_content
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            get_content(self.request)

        path = '/contents/{}@{}:{}.json'.format(
            book_uuid, book_version, page_uuid)
        self.assertEqual(cm.exception.headers['Location'], quote(path))

    def test_legacy_id_redirect(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        objid = 'm42709'

        # Build the request environment.
        self.request.matchdict = {'objid': objid}

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
        cursor.execute('''INSERT INTO files (file) VALUES
            (%s) RETURNING fileid''', [memoryview(b'Version 4')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename, mimetype) VALUES
                       (%s, %s, 'index.cnxml.html', 'text/html')''',
                       [16, fileid])
        # Insert a file for version 5
        cursor.execute('''INSERT INTO files (file) VALUES
            (%s) RETURNING fileid''', [memoryview(b'Version 5')])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
                       (module_ident, fileid, filename, mimetype) VALUES
                       (%s, %s, 'index.cnxml.html', 'text/html')''',
                       [15, fileid])
        cursor.connection.commit()

        def get_content(version):
            # Build the request environment
            self.request.matchdict = {'ident_hash': '{}@{}'.format(uuid, version)}

            # Call the view
            from ..views import get_content
            content = get_content(self.request).json_body

            return content.pop('content')

        self.assertEqual(get_content(4), 'Version 4')
        self.assertEqual(get_content(5), 'Version 5')

    def test_content_collection_as_html(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        expected = """<html xmlns="http://www.w3.org/1999/xhtml">
  <body>\
<ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597%407.1.html">College Physics</a>\
<ul><li><a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e%407.html">Preface</a></li>\
<li><a>Introduction: The Nature of Science and Physics</a>\
<ul><li><a href="/contents/f3c9ab70-a916-4d8c-9256-42953287b4e9%403.html">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a></li>\
<li><a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce%404.html">Physics: An Introduction</a></li>\
<li><a href="/contents/c8bdbabc-62b1-4a5f-b291-982ab25756d7%406.html">Physical Quantities and Units</a></li>\
<li><a href="/contents/5152cea8-829a-4aaf-bcc5-c58a416ecb66%407.html">Accuracy, Precision, and Significant Figures</a></li>\
<li><a href="/contents/5838b105-41cd-4c3d-a957-3ac004a48af3%405.html">Approximation</a></li></ul></li>\
<li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a>\
<ul><li><a href="/contents/24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d%402.html">Introduction: Further Applications of Newton’s Laws</a></li>\
<li><a href="/contents/ea271306-f7f2-46ac-b2ec-1d80ff186a59%405.html">Friction</a></li>\
<li><a href="/contents/26346a42-84b9-48ad-9f6a-62303c16ad41%406.html">Drag Forces</a></li>\
<li><a href="/contents/56f1c5c1-4014-450d-a477-2121e276beca%408.html">Elasticity: Stress and Strain</a></li>\
</ul></li><li><a href="/contents/f6024d8a-1868-44c7-ab65-45419ef54881%403.html">Atomic Masses</a></li>\
<li><a href="/contents/7250386b-14a7-41a2-b8bf-9e9ab872f0dc%402.html">Selected Radioactive Isotopes</a></li>\
<li><a href="/contents/c0a76659-c311-405f-9a99-15c71af39325%405.html">Useful Inførmation</a></li>\
<li><a href="/contents/ae3e18de-638d-4738-b804-dc69cd4db3a3%405.html">Glossary of Key Symbols and Notation</a></li></ul></li></ul></body>\n</html>\n"""

        # Build the environment
        self.request.matchdict = {
            'ident_hash': '{}@{}'.format(uuid, version),
            }

        # Call the view
        from ..views import get_content_html
        resp = get_content_html(self.request)

        # Check that the view returns the expected html
        if IS_PY2:
            p = HTMLParser.HTMLParser()
            resp_body = p.unescape(resp.body)
        else:
            resp_body = html.unescape(resp.body.decode('utf-8'))
        self.assertEqual(resp_body, expected)

    def test_content_module_as_html(self):
        uuid = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce'
        version = '4'

        # Build the request environment.
        self.request.matchdict = {'ident_hash': "{}@{}".format(uuid, version)}

        # Call the view.
        from ..views import get_content_html

        # Check that the view returns some html
        resp_body = get_content_html(self.request).body
        self.assertTrue(resp_body.startswith(b'<html'))

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        hash = '075500ad9f71890a85fe3f7a4137ac08e2b7907c'

        # Build the request.
        self.request.matchdict = {'hash': hash}

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

        from ..views import get_export
        export = get_export(self.request).body

        self.assertEqual(self.request.response.content_disposition,
                         "attached; filename=college-physics-{}.pdf"
                         .format(version))
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'exports',
                                     filename)
        with open(expected_file, 'rb') as file:
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
            self.assertEqual(export.decode('utf-8'), file.read())

    def test_exports_type_not_supported(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '56f1c5c1-4014-450d-a477-2121e276beca@8',
                'type': 'txt'
                }

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_404(self):
        # Build the request
        self.request.matchdict = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                          get_export, self.request)

    def test_exports_without_version(self):
        id = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request
        self.request.matchdict = {'ident_hash': id, 'type': 'pdf'}

        from ..views import get_export
        with self.assertRaises(httpexceptions.HTTPFound) as cm:
            get_export(self.request)

        self.assertEqual(cm.exception.status, '302 Found')
        self.assertEqual(cm.exception.headers['Location'],
                         quote('/exports/{}@5.pdf'.format(id)))

    def test_get_extra_no_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            'downloads': [{
                'created': None,
                'details': 'PDF file, for viewing content offline and printing.',
                'filename': 'college-physics-6.1.pdf',
                'format': 'PDF',
                'path': quote('/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.pdf/college-physics-6.1.pdf'),
                'size': 0,
                'state': 'missing'},
               {
                'created': None,
                'details': 'Electronic book format file, for viewing on mobile devices.',
                'filename': 'college-physics-6.1.epub',
                'format': 'EPUB',
                'path': quote('/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.epub/college-physics-6.1.epub'),
                'size': 0,
                'state': 'missing'},
               {
                'created': None,
                'details': 'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                'filename': 'college-physics-6.1.zip',
                'format': 'Offline ZIP',
                'path': quote('/exports/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.1.zip/college-physics-6.1.zip'),
                'size': 0,
                'state': 'missing'}],
            'isLatest': False,
            'canPublish': [
                'OpenStaxCollege',
                'cnxcap',
                ],
            })

    def test_get_extra_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                'created': '2015-03-04T10:03:29-08:00',
                'format': 'PDF',
                'size': 28,
                'state': 'good',
                'filename': 'college-physics-{}.pdf'.format(version),
                'details': 'PDF file, for viewing content offline and printing.',
                'path': quote('/exports/{}@{}.pdf/college-physics-{}.pdf'.format(
                    id, version, version)),
                },
            {
                'created': '2015-03-04T10:03:29-08:00',
                'format': 'EPUB',
                'size': 13,
                'state': 'good',
                'filename': 'college-physics-{}.epub'.format(version),
                'details': 'Electronic book format file, for viewing on mobile devices.',
                'path': quote('/exports/{}@{}.epub/college-physics-{}.epub'.format(
                    id, version, version)),
                },
            {
                'created': '2015-03-04T10:03:29-08:00',
                'format': 'Offline ZIP',
                'size': 11,
                'state': 'good',
                'filename': 'college-physics-{}.zip'.format(version),
                'details': 'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                'path': quote('/exports/{}@{}.zip/college-physics-{}.zip'.format(
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

        # Call the target
        from ..views import get_extra
        output = get_extra(self.request).json_body

        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        self.assertEqual(output['downloads'], [
            {
                'path': quote('/exports/{}@{}.pdf/preface-to-college-physics-7.pdf'
                              .format(id, version)),
                'format': 'PDF',
                'created': '2015-03-04T10:03:29-08:00',
                'state': 'good',
                'size': 15,
                'details': 'PDF file, for viewing content offline and printing.',
                'filename': 'preface-to-college-physics-7.pdf',
                },
            {
                'path': quote('/exports/{}@{}.epub/preface-to-college-physics-7.epub'
                              .format(id, version)),
                'format': 'EPUB',
                'created': '2015-03-04T10:03:29-08:00',
                'state': 'good',
                'size': 16,
                'details': 'Electronic book format file, for viewing on mobile devices.',
                'filename': 'preface-to-college-physics-7.epub',
                },
            {
                'created': None,
                'details': 'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                'filename': 'preface-to-college-physics-7.zip',
                'format': 'Offline ZIP',
                'path': quote('/exports/209deb1f-1a46-4369-9e0d-18674cf58a3e@7.zip/preface-to-college-physics-7.zip'),
                'size': 0,
                'state': 'missing'}
            ])

    def test_extra_latest(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

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

        # Call the target
        from ..views import get_extra
        with self.assertRaises(httpexceptions.HTTPFound) as raiser:
            get_extra(self.request)
        exception = raiser.exception
        expected_location = "/extras/{}".format(expected_ident_hash)
        self.assertEqual(exception.headers['Location'],
                         quote(expected_location))

    def test_extra_w_utf8_characters(self):
        id = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = '5'
        ident_hash = '{}@{}'.format(id, version)

        # Build the request
        self.request.matchdict = {'ident_hash': ident_hash}

        # Call the target
        from ..views import get_extra
        output = get_extra(self.request).json_body
        self.assertEqual(self.request.response.status, '200 OK')
        self.assertEqual(self.request.response.content_type,
                         'application/json')
        output['canPublish'].sort()
        self.assertEqual(output, {
            'canPublish': [
                'OpenStaxCollege',
                'cnxcap',
                ],
            'isLatest': True,
            'downloads': [{
                'created': '2015-03-04T10:03:29-08:00',
                'path': quote('/exports/{}@{}.pdf/useful-inførmation-5.pdf'
                              .format(id, version).encode('utf-8')),
                'format': 'PDF',
                'details': 'PDF file, for viewing content offline and printing.',
                'filename': 'useful-inførmation-5.pdf',
                'size': 0,
                'state': 'good'},
                {
                'created': None,
                'details': 'Electronic book format file, for viewing on mobile devices.',
                'filename': 'useful-inf\xf8rmation-5.epub',
                'format': 'EPUB',
                'path': quote('/exports/{}@{}.epub/useful-inførmation-5.epub'
                              .format(id, version).encode('utf-8')),
                'size': 0,
                'state': 'missing'},
                {
                'created': None,
                'details': 'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                'filename': 'useful-inf\xf8rmation-5.zip',
                'format': 'Offline ZIP',
                'path': quote('/exports/{}@{}.zip/useful-inførmation-5.zip'
                              .format(id, version).encode('utf-8')),
                'size': 0,
                'state': 'missing'}],
            })

    def test_extra_not_found(self):
        # Test version not found
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.1'

        # Build the request
        self.request.matchdict = {'ident_hash': '{}@{}'.format(id, version)}

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

    def test_search(self):
        # Build the request
        self.request.params = {'q': '"college physics" sort:version'}

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

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['query'], {
            'sort': [],
            'per_page': 20,
            'page': 1,
            'limits': [{'tag': 'text', 'value': 'college physics'},
                       {'tag': 'authorID', 'index': 0,
                        'value': 'cnxcap'}],
            })

    def test_author_special_case_search(self):
        '''
        Test the search case where an additional database query is needed to
        return auxiliary author info when the first query returned no
        results.
        '''

        # Build the request
        sub = 'subject:"Arguing with Judge Judy: Popular ‘Logic’ on TV Judge Shows"'
        auth0 = 'authorID:cnxcap'
        auth1 = 'authorID:OpenStaxCollege'
        auth2 = 'authorID:DrBunsenHoneydew'
        fields = [sub, auth0, auth1, auth2]
        self.request.params = {'q': ' '.join(fields)}

        from ..views import search
        results = search(self.request).json_body

        self.assertEqual(results['results']['total'], 0)

        expected = [
            {'surname': 'Physics',
             'firstname': 'College',
             'suffix': None,
             'title': None,
             'fullname': 'OSC Physics Maintainer',
             'id': 'cnxcap',
             },
            {'surname': None,
             'firstname': 'OpenStax College',
             'suffix': None,
             'title': None,
             'fullname': 'OpenStax College',
             'id': 'OpenStaxCollege',
             },
            {'fullname': None,
             'id': 'DrBunsenHoneydew',
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

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'per_page': 20,
            'page': 1,
            'limits': [{'tag': 'subject', 'value': 'Science and Technology'}],
            'sort': []})
        self.assertEqual(results['results']['total'], 7)

    def test_search_with_subject(self):
        # Build the request
        self.request.params = {'q': 'title:"college physics" subject:"Science and Technology"'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query'], {
            'per_page': 20,
            'page': 1,
            'limits': [
                {'tag': 'title', 'value': 'college physics'},
                {'tag': 'subject', 'value': 'Science and Technology'},
                ],
            'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_highlight_abstract(self):
        # Build the request
        self.request.params = {'q': '"college physics"'}

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
        self.assertEqual(results['results']['items'][2]['summarySnippet'], None)

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

        self.assertEqual(results['results']['items'][2]['summarySnippet'], None)

    def test_search_no_params(self):
        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results, {
            'query': {
                'limits': [],
                'per_page': 20,
                'page': 1,
                },
            'results': {
                'items': [],
                'total': 0,
                'limits': [],
                },
            })

    def test_search_whitespace(self):
        self.request.params = {'q': ' '}

        from ..views import search
        results = search(self.request).body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results.decode('utf-8'), json.dumps({
            'query': {
                'limits': [],
                'per_page': 20,
                'page': 1,
                },
            'results': {
                'items': [],
                'total': 0,
                'limits': [],
                },
            }))

    def test_search_utf8(self):
        self.request.params = {'q': '"你好"'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            'query': {
                'limits': [{'tag': 'text', 'value': '你好'}],
                'sort': [],
                'per_page': 20,
                'page': 1,
                },
            'results': {
                'items': [],
                'total': 0,
                'limits': [
                    {'tag': 'type',
                     'values': [
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.collection'},
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                'auxiliary': {
                    'authors': [],
                    'types': [
                        {'name': 'Book',
                         'id': 'application/vnd.org.cnx.collection'},
                        {'name': 'Page',
                         'id': 'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_punctuations(self):
        self.request.params = {'q': r":\.+'?"}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            'query': {
                'limits': [{'tag': 'text', 'value': ":\.+'?"}],
                'sort': [],
                'per_page': 20,
                'page': 1,
                },
            'results': {
                'items': [],
                'total': 0,
                'limits': [
                    {'tag': 'type',
                     'values': [
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.collection'},
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                'auxiliary': {
                    'authors': [],
                    'types': [
                        {'name': 'Book',
                         'id': 'application/vnd.org.cnx.collection'},
                        {'name': 'Page',
                         'id': 'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_unbalanced_quotes(self):
        self.request.params = {'q': r'"a phrase" "something else sort:pubDate author:"first last"'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        expected = {
            'query': {
                'limits': [
                    {'tag': 'text', 'value': 'a phrase'},
                    {'tag': 'text', 'value': 'something else'},
                    {'tag': 'author', 'value': 'first last'},
                    ],
                'sort': ['pubDate'],
                'per_page': 20,
                'page': 1,
                },
            'results': {
                'items': [],
                'total': 0,
                'limits': [
                    {'tag': 'type',
                     'values': [
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.collection'},
                         {'count': 0,
                          'value': 'application/vnd.org.cnx.module'},
                         ],
                     },
                    ],
                'auxiliary': {
                    'authors': [],
                    'types': [
                        {'name': 'Book',
                         'id': 'application/vnd.org.cnx.collection'},
                        {'name': 'Page',
                         'id': 'application/vnd.org.cnx.module'},
                        ],
                    },
                },
            }
        self.assertEqual(results, expected)

    def test_search_type_page_or_module(self):
        # Test searching "page"

        # Build the request
        self.request.params = {'q': 'title:"college physics" type:page'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {'tag': 'type', 'value': 'page'})
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
                         {'tag': 'type', 'value': 'module'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'application/vnd.org.cnx.module')

    def test_search_type_book_or_collection(self):
        # Test searching "book"

        # Build the request
        self.request.params = {'q': 'title:physics type:book'}

        from ..views import search
        results = search(self.request).json_body
        status = self.request.response.status
        content_type = self.request.response.content_type

        self.assertEqual(status, '200 OK')
        self.assertEqual(content_type, 'application/json')

        self.assertEqual(results['query']['limits'][-1],
                         {'tag': 'type', 'value': 'book'})
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
                         {'tag': 'type', 'value': 'collection'})
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
                'Introduction: Further Applications of Newton’s Laws')
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

        # Call the view
        from ..views import extras
        metadata = extras(self.request).json_body
        messages = metadata.pop('messages')
        self.assertEqual(metadata, {
            'subjects': [{'id': 1, 'name': 'Arts',
                          'count': {'module': 0, 'collection': 0},
                          },
                         {'id': 2, 'name': 'Business',
                          'count': {'module': 0, 'collection': 0},
                          },
                         {'id': 3, 'name': 'Humanities',
                          'count': {'module': 0, 'collection': 0},
                          },
                         {'id': 4, 'name': 'Mathematics and Statistics',
                          'count': {'module': 7, 'collection': 1},
                          },
                         {'id': 5, 'name': 'Science and Technology',
                          'count': {'module': 6, 'collection': 1},
                          },
                         {'id': 6, 'name': 'Social Sciences',
                          'count': {'module': 0, 'collection': 0},
                          }],
            'featuredLinks': [{
                'id': 'e79ffde3-7fb4-4af3-9ec8-df648b391597',
                'title': 'College Physics',
                'version': '7.1',
                'legacy_id': 'col11406',
                'legacy_version': '1.7',
                'resourcePath': '/resources/6214e8dcdf2824dbf830b4a0d77a3fa2f53608d2',
                'type': 'OpenStax Featured',
                'abstract': """<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" \
xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">\
This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. \
This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics \
application problems.</div>""",
                }],
            'licenses': [{'code': 'by',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution License',
                          'url': 'http://creativecommons.org/licenses/by/1.0',
                          'version': '1.0'},
                         {'code': 'by-nd',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NoDerivs License',
                          'url': 'http://creativecommons.org/licenses/by-nd/1.0',
                          'version': '1.0'},
                         {'code': 'by-nd-nc',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NoDerivs-NonCommercial License',
                          'url': 'http://creativecommons.org/licenses/by-nd-nc/1.0',
                          'version': '1.0'},
                         {'code': 'by-nc',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NonCommercial License',
                          'url': 'http://creativecommons.org/licenses/by-nc/1.0',
                          'version': '1.0'},
                         {'code': 'by-sa',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-ShareAlike License',
                          'url': 'http://creativecommons.org/licenses/by-sa/1.0',
                          'version': '1.0'},
                         {'code': 'by',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution License',
                          'url': 'http://creativecommons.org/licenses/by/2.0/',
                          'version': '2.0'},
                         {'code': 'by-nd',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NoDerivs License',
                          'url': 'http://creativecommons.org/licenses/by-nd/2.0',
                          'version': '2.0'},
                         {'code': 'by-nd-nc',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NoDerivs-NonCommercial License',
                          'url': 'http://creativecommons.org/licenses/by-nd-nc/2.0',
                          'version': '2.0'},
                         {'code': 'by-nc',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-NonCommercial License',
                          'url': 'http://creativecommons.org/licenses/by-nc/2.0',
                          'version': '2.0'},
                         {'code': 'by-sa',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution-ShareAlike License',
                          'url': 'http://creativecommons.org/licenses/by-sa/2.0',
                          'version': '2.0'},
                         {'code': 'by',
                          'isValidForPublication': False,
                          'name': 'Creative Commons Attribution License',
                          'url': 'http://creativecommons.org/licenses/by/3.0/',
                          'version': '3.0'},
                         {'code': 'by',
                          'isValidForPublication': True,
                          'name': 'Creative Commons Attribution License',
                          'url': 'http://creativecommons.org/licenses/by/4.0/',
                          'version': '4.0'},
                         {'code': 'by-nc-sa',
                          'isValidForPublication': True,
                          'name': 'Creative Commons Attribution-NonCommercial-ShareAlike License',
                          'url': 'http://creativecommons.org/licenses/by-nc-sa/4.0/',
                          'version': '4.0'}],
            })
        expected_messages = [
            {'message': 'This site is scheduled to be down for maintaince, please excuse the interuption. Thank you.',
             'name': 'Maintenance',
             'priority': 1},
            {'message': "We have free books at free prices! Don't miss out!",
             'name': 'Notice',
             'priority': 8}
            ]

        def _remove_timestamps(messages):
            for message in messages:
                message.pop('starts')
                message.pop('ends')
            return messages
        self.assertEqual(expected_messages, _remove_timestamps(messages))

    def test_sitemap(self):
        # Call the view
        from ..views import sitemap
        sitemap = sitemap(self.request).body
        expected_file = os.path.join(testing.DATA_DIRECTORY, 'sitemap.xml')
        with open(expected_file, 'r') as file:
            self.assertMultiLineEqual(sitemap.decode('utf-8'), file.read())

    def test_robots(self):
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
            self.assertMultiLineEqual(robots.decode('utf-8'), f.read())
