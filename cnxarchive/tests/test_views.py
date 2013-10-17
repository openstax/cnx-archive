# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import json
import unittest
from wsgiref.util import setup_testing_defaults

import psycopg2

from . import *
from .. import httpexceptions


COLLECTION_METADATA = {
    u'roles': None,
    u'subject': u'Mathematics and Statistics,Science and Technology',
    u'abstract': u'This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics application problems.',
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31 12:07:20.342798-07',
    u'doctype': u'',
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [{u'website': None, u'surname': u'University',
                    u'suffix': None, u'firstname': u'Rice',
                    u'title': None, u'othername': None,
                    u'id': u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                    u'fullname': u'Rice University',
                    u'email': u'daniel@openstaxcollege.org'},
                   ],
    u'maintainers': [{u'website': None, u'surname': u'Physics',
                      u'suffix': None, u'firstname': u'College',
                      u'title': None, u'othername': None,
                      u'id': u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                      u'fullname': u'OSC Physics Maintainer',
                      u'email': u'info@openstaxcollege.org'},
                     {u'website': None, u'surname': None,
                      u'suffix': None, u'firstname': u'OpenStax College',
                      u'title': None, u'othername': None,
                      u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                      u'fullname': u'OpenStax College',
                      u'email': u'info@openstaxcollege.org'},
                     ],
    u'title': u'College Physics',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentVersion': '',
    u'revised': u'2013-08-31 12:07:20.342798-07',
    u'stateid': None,
    u'submitlog': u'New version 1.7',
    u'submitter': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
    u'mediaType': u'application/vnd.org.cnx.collection',
    u'version': u'1.7',
    u'googleAnalytics': u'UA-XXXXX-Y',
    u'buyLink': None,
    u'legacy_id':u'col11406',
    u'legacy_version':u'1.7',
    u'history': [
        {
            u'version': u'1.7',
            u'revised': u'2013-08-31 12:07:20.342798-07',
            u'changes': 'New version 1.7',
            u'publisher': {
                u'website': None, u'surname': None,
                u'suffix': None, u'firstname': u'OpenStax College',
                u'title': None, u'othername': None,
                u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                u'fullname': u'OpenStax College',
                u'email': u'info@openstaxcollege.org'
                },
            },
        {
            u'version': u'1.6',
            u'revised': u'2013-07-31 12:07:20.342798-07',
            u'changes': 'Updated something',
            u'publisher': {
                u'website': None, u'surname': None,
                u'suffix': None, u'firstname': u'OpenStax College',
                u'title': None, u'othername': None,
                u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                u'fullname': u'OpenStax College',
                u'email': u'info@openstaxcollege.org'
                },
            },
        ],
    }
COLLECTION_JSON_TREE = {
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@1.7',
    u'title': u'College Physics',
    u'contents': [
        {u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
         u'title': u'Preface'},
        {u'id': u'subcol',
         u'title': u'Introduction: The Nature of Science and Physics',
         u'contents': [
                {u'id': u'f3c9ab70-a916-4d8c-9256-42953287b4e9@3',
                 u'title': u'Introduction to Science and the Realm of Physics, Physical Quantities, and Units'},
                {u'id': u'd395b566-5fe3-4428-bcb2-19016e3aa3ce@4',
                 u'title': u'Physics: An Introduction'},
                {u'id': u'c8bdbabc-62b1-4a5f-b291-982ab25756d7@6',
                 u'title': u'Physical Quantities and Units'},
                {u'id': u'5152cea8-829a-4aaf-bcc5-c58a416ecb66@7',
                 u'title': u'Accuracy, Precision, and Significant Figures'},
                {u'id': u'5838b105-41cd-4c3d-a957-3ac004a48af3@5',
                 u'title': u'Approximation'},
                ],
         },
        {u'id': u'subcol',
         u'title': u"Further Applications of Newton's Laws: Friction, Drag, and Elasticity",
         u'contents': [
                {u'id': u'24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2',
                 u'title': u'Introduction: Further Applications of Newton\u2019s Laws'},
                {u'id': u'ea271306-f7f2-46ac-b2ec-1d80ff186a59@5',
                 u'title': u'Friction'},
                {u'id': u'26346a42-84b9-48ad-9f6a-62303c16ad41@6',
                 u'title': u'Drag Forces'},
                {u'id': u'56f1c5c1-4014-450d-a477-2121e276beca@8',
                 u'title': u'Elasticity: Stress and Strain'},
                ],
         },
        {u'id': u'f6024d8a-1868-44c7-ab65-45419ef54881@3',
         u'title': u'Atomic Masses'},
        {u'id': u'7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2',
         u'title': u'Selected Radioactive Isotopes'},
        {u'id': u'c0a76659-c311-405f-9a99-15c71af39325@5',
         u'title': u'Useful Information'},
        {u'id': u'ae3e18de-638d-4738-b804-dc69cd4db3a3@4',
         u'title': u'Glossary of Key Symbols and Notation'},
        ],
    }
MODULE_METADATA = {
    u'roles': None,
    u'subject': u'Science and Technology',
    u'abstract': None,
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31 12:07:24.856663-07',
    u'doctype': u'',
    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca',
    u'language': u'en',
    u'license': u'http://creativecommons.org/licenses/by/3.0/',
    u'licensors': [{u'website': None, u'surname': u'University',
                    u'suffix': None, u'firstname': u'Rice',
                    u'title': None, u'othername': None,
                    u'id': u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                    u'fullname': u'Rice University',
                    u'email': u'daniel@openstaxcollege.org'},
                   ],
    u'maintainers': [{u'website': None, u'surname': u'Physics',
                      u'suffix': None, u'firstname': u'College',
                      u'title': None, u'othername': None,
                      u'id': u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                      u'fullname': u'OSC Physics Maintainer',
                      u'email': u'info@openstaxcollege.org'},
                     {u'website': None, u'surname': None,
                      u'suffix': None, u'firstname': u'OpenStax College',
                      u'title': None, u'othername': None,
                      u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                      u'fullname': u'OpenStax College',
                      u'email': u'info@openstaxcollege.org'},
                     ],
    u'title': u'Elasticity: Stress and Strain',
    u'parentAuthors': [],
    u'parentId': None,
    u'parentVersion': '',
    u'revised': u'2013-07-31 12:07:24.856663-07',
    u'stateid': None,
    u'submitlog': u'Added more examples',
    u'submitter': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
    u'mediaType': u'application/vnd.org.cnx.module',
    u'version': u'8',
    u'googleAnalytics': None,
    u'buyLink': u'http://openstaxcollege.worksmartsuite.com/',
    u'legacy_id':u'm42081',
    u'legacy_version':u'1.8',
    u'history': [
        {
            u'version': u'8',
            u'revised': u'2013-07-31 12:07:24.856663-07',
            u'changes': u'Added more examples',
            u'publisher': {
                u'website': None, u'surname': None,
                u'suffix': None, u'firstname': u'OpenStax College',
                u'title': None, u'othername': None,
                u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                u'fullname': u'OpenStax College',
                u'email': u'info@openstaxcollege.org',
                },
            },
        ],
    }
SEARCH_RESULTS = {
    u'query': {
        u'limits': [{u'text': u'college physics'}],
        u'sort': [u'version'],
        },
    u'results': {
        u'items': [
            {u'authors': [{u'email': u'info@openstaxcollege.org',
                           u'firstname': u'OpenStax College',
                           u'fullname': u'OpenStax College',
                           u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                           u'othername': None,
                           u'suffix': None,
                           u'surname': None,
                           u'title': None,
                           u'website': None}],
             u'bodySnippet': u'<b>College</b> <b>Physics</b>\n\nPreface to <b>College</b> <b>Physics</b>\n    About OpenStax <b>College</b>\nOpenStax <b>College</b> is a non-profit organization committed to improving student access to quality learning materials. Our free textbooks are developed and peer-reviewed by educators to ensure they are readable, accurate, and meet the scope and sequence requirements of modern',
             u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e',
             u'keywords': [u'college physics',
                           u'introduction',
                           u'physics'],
             u'mediaType': u'Module',
             u'pubDate': u'2013-07-31 12:07:20.542211-07',
             u'summarySnippet': None,
             u'title': u'Preface to College Physics'},
            {u'authors': [{u'email': u'info@openstaxcollege.org',
                           u'firstname': u'OpenStax College',
                           u'fullname': u'OpenStax College',
                           u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                           u'othername': None,
                           u'suffix': None,
                           u'surname': None,
                           u'title': None,
                           u'website': None}],
             u'bodySnippet': None,
             u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
             u'keywords': [u'college physics',
                           u'physics',
                           u'friction',
                           u'ac circuits',
                           u'atomic physics',
                           u'bioelectricity',
                           u'biological and medical applications',
                           u'circuits',
                           u'collisions',
                           u'dc instruments',
                           u'drag',
                           u'elasticity',
                           u'electric charge and electric field',
                           u'electric current',
                           u'electric potential',
                           u'electrical technologies',
                           u'electromagnetic induction',
                           u'electromagnetic waves',
                           u'energy',
                           u'fluid dynamics',
                           u'fluid statics',
                           u'forces',
                           u'frontiers of physics',
                           u'gas laws',
                           u'geometric optics',
                           u'heat and transfer methods',
                           u'kinematics',
                           u'kinetic theory',
                           u'linear momentum',
                           u'magnetism',
                           u'medical applications of nuclear physics',
                           u'Newton\u2019s Laws of Motion',
                           u'Ohm\u2019s Law',
                           u'oscillatory motion and waves',
                           u'particle physics',
                           u'physics of hearing',
                           u'quantum physics',
                           u'radioactivity and nuclear physics',
                           u'resistance',
                           u'rotational motion and angular momentum',
                           u'special relativity',
                           u'statics and torque',
                           u'temperature',
                           u'thermodynamics',
                           u'uniform circular motion and gravitation',
                           u'vision and optical instruments',
                           u'wave optics',
                           u'work'],
             u'mediaType': u'Collection',
             u'pubDate': u'2013-07-31 12:07:20.342798-07',
             u'summarySnippet': u'algebra-based, two-semester <b>college</b> <b>physics</b> book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental <b>physics</b> concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional <b>physics</b> application problems.',
             u'title': u'College Physics'},
            ],
        u'total': 2,
        u'limits': [
            {u'count': 2, u'pubYear': u'2013'},
            {u'author': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
             u'count': 2},
            {u'count': 1,
             u'mediaType': u'application/vnd.org.cnx.collection'},
            {u'count': 1, u'mediaType': u'application/vnd.org.cnx.module'},
            {u'count': 1, u'keyword': u'work'},
            {u'count': 1, u'keyword': u'electric potential'},
            {u'count': 1, u'keyword': u'energy'},
            {u'count': 1, u'keyword': u'ac circuits'},
            {u'count': 1, u'keyword': u'elasticity'},
            {u'count': 1, u'keyword': u'friction'},
            {u'count': 1, u'keyword': u'vision and optical instruments'},
            {u'count': 1, u'keyword': u'fluid statics'},
            {u'count': 1, u'keyword': u'statics and torque'},
            {u'count': 1, u'keyword': u'radioactivity and nuclear physics'},
            {u'count': 1,
             u'keyword': u'uniform circular motion and gravitation'},
            {u'count': 1, u'keyword': u'particle physics'},
            {u'count': 1,
             u'keyword': u'biological and medical applications'},
            {u'count': 1, u'keyword': u'fluid dynamics'},
            {u'count': 1, u'keyword': u'quantum physics'},
            {u'count': 1, u'keyword': u'thermodynamics'},
            {u'count': 1, u'keyword': u'introduction'},
            {u'count': 1, u'keyword': u'Newton\u2019s Laws of Motion'},
            {u'count': 1, u'keyword': u'atomic physics'},
            {u'count': 2, u'keyword': u'college physics'},
            {u'count': 1, u'keyword': u'collisions'},
            {u'count': 1, u'keyword': u'electric charge and electric field'},
            {u'count': 1, u'keyword': u'kinematics'},
            {u'count': 1, u'keyword': u'forces'},
            {u'count': 1, u'keyword': u'electrical technologies'},
            {u'count': 1,
             u'keyword': u'rotational motion and angular momentum'},
            {u'count': 1,
             u'keyword': u'medical applications of nuclear physics'},
            {u'count': 1, u'keyword': u'wave optics'},
            {u'count': 1, u'keyword': u'kinetic theory'},
            {u'count': 1, u'keyword': u'special relativity'},
            {u'count': 1, u'keyword': u'heat and transfer methods'},
            {u'count': 1, u'keyword': u'resistance'},
            {u'count': 1, u'keyword': u'drag'},
            {u'count': 1, u'keyword': u'electric current'},
            {u'count': 1, u'keyword': u'dc instruments'},
            {u'count': 1, u'keyword': u'electromagnetic waves'},
            {u'count': 1, u'keyword': u'frontiers of physics'},
            {u'count': 1, u'keyword': u'physics of hearing'},
            {u'count': 1, u'keyword': u'gas laws'},
            {u'count': 1, u'keyword': u'temperature'},
            {u'count': 1, u'keyword': u'electromagnetic induction'},
            {u'count': 1, u'keyword': u'circuits'},
            {u'count': 1, u'keyword': u'oscillatory motion and waves'},
            {u'count': 1, u'keyword': u'geometric optics'},
            {u'count': 1, u'keyword': u'magnetism'},
            {u'count': 1, u'keyword': u'linear momentum'},
            {u'count': 1, u'keyword': u'bioelectricity'},
            {u'count': 1, u'keyword': u'Ohm\u2019s Law'},
            {u'count': 2, u'keyword': u'physics'},
            {u'count': 2, u'subject': u'Mathematics and Statistics'},
            {u'count': 1, u'subject': u'Science and Technology'}],
        }
    }

class ViewsTestCase(unittest.TestCase):
    fixture = postgresql_fixture
    maxDiff = 10000

    @classmethod
    def setUpClass(cls):
        from ..utils import parse_app_settings
        cls.settings = parse_app_settings(TESTING_CONFIG)
        from ..database import CONNECTION_SETTINGS_KEY
        cls.db_connection_string = cls.settings[CONNECTION_SETTINGS_KEY]
        cls._db_connection = psycopg2.connect(cls.db_connection_string)

    @classmethod
    def tearDownClass(cls):
        cls._db_connection.close()

    def setUp(self):
        from .. import _set_settings
        _set_settings(self.settings)
        self.fixture.setUp()
        # Load the database with example legacy data.
        with self._db_connection.cursor() as cursor:
            with open(TESTING_DATA_SQL_FILE, 'rb') as fb:
                cursor.execute(fb.read())
            # Populate the cnx-user shadow.
            with open(TESTING_CNXUSER_DATA_SQL_FILE, 'r') as fb:
                cursor.execute(fb.read())
        self._db_connection.commit()

        self.settings['exports-directories'] = ' '.join([
                os.path.join(TEST_DATA_DIRECTORY, 'exports'),
                os.path.join(TEST_DATA_DIRECTORY, 'exports2')
                ])
        self.settings['exports-allowable-types'] = '''
            pdf:pdf,application/pdf,PDF,PDF file, for viewing content offline and printing.
            epub:epub,application/epub+zip,EPUB,Electronic book format file, for viewing on mobile devices.
            zip:zip,application/zip,Offline ZIP,An offline HTML copy of the content.  Also includes XML, included media files, and other support files.
        '''

    def tearDown(self):
        from .. import _set_settings
        _set_settings(None)
        self.fixture.tearDown()

    def _make_environ(self):
        environ = {}
        setup_testing_defaults(environ)
        return environ

    def _start_response(self, status, headers=[]):
        """Used to capture the WSGI 'start_response'."""
        self.captured_response = {'status': status, 'headers': headers}

    def test_collection_content(self):
        # Test for retrieving a piece of content.
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.7'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from ..views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

        # Remove the 'tree' from the content for separate testing.
        content_tree = content.pop('tree')

        # Check the metadata for correctness.
        self.assertEqual(sorted(content.keys()), sorted(COLLECTION_METADATA.keys()))
        for key in content:
            self.assertEqual(content[key], COLLECTION_METADATA[key],
                    'content[{key}] = {v1} but COLLECTION_METADATA[{key}] = {v2}'.format(
                        key=key, v1=content[key], v2=COLLECTION_METADATA[key]))

        self.maxDiff = 10000
        # Check the tree for accuracy.
        self.assertEqual(content_tree, COLLECTION_JSON_TREE)

    def test_module_content(self):
        # Test for retreiving a module.
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from ..views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

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
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}".format(uuid)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from ..views import get_content

        # Check that the view redirects to the latest version
        try:
            get_content(environ, self._start_response)
            self.assert_(False, 'should not get here')
        except httpexceptions.HTTPFound, e:
            self.assertEqual(e.status, '302 Found')
            self.assertEqual(e.headers, [('Location',
                '/contents/{}@5'.format(uuid))])

    def test_resources(self):
        # Test the retrieval of resources contained in content.
        hash = '8c48c59e411d1e31cc0186be535fa5eb'

        # Build the request.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'hash': hash}

        # Call the view.
        from ..views import get_resource
        resource = get_resource(environ, self._start_response)[0]

        expected_bits = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xfe\x00\x00\x00\x93\x08\x06\x00\x00\x00\xf6\x90\x1d\x14'
        # Check the response body.
        self.assertEqual(bytes(resource)[:len(expected_bits)],
                         expected_bits)

        # Check for response headers, specifically the content-disposition.
        headers = self.captured_response['headers']
        expected_headers = [
            ('Content-type', 'image/png',),
            ]
        self.assertEqual(headers, expected_headers)

    def test_exports(self):
        # Test for the retrieval of exports (e.g. pdf files).
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.7'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        filename = "{}-{}.{}".format(id, version, type)

        # Build the request.
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash,
                                           'type': type,
                                           }

        from ..views import get_export
        export = get_export(environ, self._start_response)[0]

        headers = self.captured_response['headers']
        headers = {x[0].lower(): x[1] for x in headers}
        self.assertEqual(headers['content-disposition'],
                         "attached; filename=college-physics.pdf")
        with open(os.path.join(TEST_DATA_DIRECTORY, 'exports', filename), 'r') as file:
            self.assertEqual(export, file.read())

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}-{}.pdf'.format(id, version)
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash,
                                           'type': 'pdf'
                                           }

        export = get_export(environ, self._start_response)[0]
        headers = self.captured_response['headers']
        headers = {x[0].lower(): x[1] for x in headers}
        self.assertEqual(headers['content-disposition'],
                         "attached; filename=elasticity-stress-and-strain.pdf")
        with open(os.path.join(TEST_DATA_DIRECTORY, 'exports2', filename), 'r') as file:
            self.assertEqual(export, file.read())

    def test_exports_type_not_supported(self):
        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {
                'ident_hash': '56f1c5c1-4014-450d-a477-2121e276beca@8',
                'type': 'txt'
                }

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                get_export, environ, self._start_response)

    def test_exports_404(self):
        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {
                'ident_hash': '24184288-14b9-11e3-86ac-207c8f4fa432@0',
                'type': 'pdf'
                }

        from ..views import get_export
        self.assertRaises(httpexceptions.HTTPNotFound,
                get_export, environ, self._start_response)

    def test_exports_without_version(self):
        id = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': id, 'type': 'pdf'}

        from ..views import get_export
        try:
            get_export(environ, self._start_response)
            self.assert_(False, 'should not get here')
        except httpexceptions.HTTPFound, e:
            self.assertEqual(e.status, '302 Found')
            self.assertEqual(e.headers, [('Location',
                '/exports/{}@5.pdf'.format(id))])

    def test_get_exports_no_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.6'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_export_allowable_types
        output = get_export_allowable_types(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output), [])

    def test_get_exports_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.7'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_export_allowable_types
        output = get_export_allowable_types(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output), [
            {
                u'format': u'PDF',
                u'filename': u'college-physics.pdf',
                u'details': u'PDF file, for viewing content offline and printing.',
                u'path': u'/exports/{}@{}.pdf'.format(id, version),
                },
            {
                u'format': u'EPUB',
                u'filename': u'college-physics.epub',
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'path': u'/exports/{}@{}.epub'.format(id, version),
                },
            {
                u'format': u'Offline ZIP',
                u'filename': u'college-physics.zip',
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'path': u'/exports/{}@{}.zip'.format(id, version),
                },
            ])

    def test_search(self):
        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q="college physics" sort:version'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(sorted(results.keys()), sorted(SEARCH_RESULTS.keys()))
        for i in results:
            self.assertEqual(results[i], SEARCH_RESULTS[i])

    def test_search_no_params(self):
        environ = self._make_environ()

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        self.assertEqual(results, json.dumps({
            u'query': {
                u'limits': [],
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
                },
            }))

    def test_search_whitespace(self):
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q= '

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        self.assertEqual(results, json.dumps({
            u'query': {
                u'limits': [],
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
                },
            }))

    def test_search_utf8(self):
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q="你好"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        self.assertEqual(json.loads(results), {
            u'query': {
                u'limits': [{u'text': u'你好'}],
                u'sort': [],
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
                },
            })

    def test_search_punctuations(self):
        environ = self._make_environ()
        # %2B is +
        environ['QUERY_STRING'] = r"q=:\.%2B'?"

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        self.assertEqual(json.loads(results), {
            u'query': {
                u'limits': [
                    {u'text': ur":\.+'?"},
                    ],
                u'sort': [],
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
                },
            })

    def test_search_unbalanced_quotes(self):
        environ = self._make_environ()
        environ['QUERY_STRING'] = r'q="a phrase" "something else sort:pubDate author:"first last"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        self.assertEqual(json.loads(results), {
            u'query': {
                u'limits': [
                    {u'text': u'a phrase'},
                    {u'text': u'something else'},
                    {u'author': 'first last'},
                    ],
                u'sort': [u'pubDate'],
                },
            u'results': {
                u'items': [],
                u'total': 0,
                u'limits': [
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.collection'},
                        {u'count': 0,
                         u'mediaType': u'application/vnd.org.cnx.module'},
                        ],
                }
            })
