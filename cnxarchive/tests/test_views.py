# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import HTMLParser
import glob
import os
import json
import unittest
from wsgiref.util import setup_testing_defaults

import psycopg2

from . import *
from .. import httpexceptions


COLLECTION_METADATA = {
    u'roles': None,
    u'subjects': [u'Mathematics and Statistics', u'Science and Technology'],
    u'abstract': u'<div xmlns="http://www.w3.org/1999/xhtml" xmlns:md="http://cnx.rice.edu/mdml" xmlns:c="http://cnx.rice.edu/cnxml" xmlns:qml="http://cnx.rice.edu/qml/1.0" xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:bib="http://bibtexml.sf.net/" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:mod="http://cnx.rice.edu/#moduleIds">This introductory, algebra-based, two-semester college physics book is grounded with real-world examples, illustrations, and explanations to help students grasp key, fundamental physics concepts. This online, fully editable and customizable title includes learning objectives, concept questions, links to labs and simulations, and ample practice opportunities to solve traditional physics application problems.</div>',
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31T19:07:20Z',
    u'doctype': u'',
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'language': u'en',
    u'license': {
        u'code': u'by',
        u'version': u'3.0',
        u'name': u'Attribution',
        u'url': u'http://creativecommons.org/licenses/by/3.0/',
        },
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
    u'parentTitle': None,
    u'parentVersion': '',
    u'revised': u'2013-08-31T19:07:20Z',
    u'stateid': None,
    u'submitlog': u'New version 1.7',
    u'submitter': {
        u'website': None, u'surname': None,
        u'suffix': None, u'firstname': u'OpenStax College',
        u'title': None, u'othername': None,
        u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
        u'fullname': u'OpenStax College',
        u'email': u'info@openstaxcollege.org'},
    u'mediaType': u'application/vnd.org.cnx.collection',
    u'version': u'7.1',
    u'googleAnalytics': u'UA-XXXXX-Y',
    u'buyLink': None,
    u'legacy_id':u'col11406',
    u'legacy_version':u'1.7',
    u'history': [
        {
            u'version': u'7.1',
            u'revised': u'2013-08-31T19:07:20Z',
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
            u'version': u'6.1',
            u'revised': u'2013-07-31T19:07:20Z',
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
    }
COLLECTION_JSON_TREE = {
    u'id': u'e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1',
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
         u'title': u'Useful Inførmation'},
        {u'id': u'ae3e18de-638d-4738-b804-dc69cd4db3a3@5',
         u'title': u'Glossary of Key Symbols and Notation'},
        ],
    }
COLLECTION_DERIVED_METADATA = {
    u'parentAuthors': [
            {u'website': None, u'surname': None, 
             u'suffix': None, u'firstname': u'OpenStax College', 
             u'title': None, u'othername': None, u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8', 
             u'fullname': u'OpenStax College', u'email': u'info@openstaxcollege.org'}],
    u'parentId': u'e79ffde3-7fb4-4af3-9ec8-df648b391597',
    u'parentTitle': u'College Physics',
    u'parentVersion': u'7.1',
    u'title': u'Derived Copy of College Physics'
}
MODULE_METADATA = {
    u'roles': None,
    u'subjects': [u'Science and Technology'],
    u'abstract': None,
    u'authors': [{u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                  u'fullname': u'OpenStax College',
                  u'email': u'info@openstaxcollege.org',
                  u'website': None, u'surname': None, u'suffix': None,
                  u'firstname': u'OpenStax College', u'title': None,
                  u'othername': None,
                  }],
    u'created': u'2013-07-31T19:07:24Z',
    u'doctype': u'',
    u'id': u'56f1c5c1-4014-450d-a477-2121e276beca',
    u'language': u'en',
    u'license': {
        u'code': u'by',
        u'version': u'3.0',
        u'name': u'Attribution',
        u'url': u'http://creativecommons.org/licenses/by/3.0/',
        },
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
    u'parentTitle': None,
    u'parentVersion': '',
    u'revised': u'2013-07-31T19:07:24Z',
    u'stateid': None,
    u'submitlog': u'Added more examples',
    u'submitter': {
        u'website': None, u'surname': None,
        u'suffix': None, u'firstname': u'OpenStax College',
        u'title': None, u'othername': None,
        u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
        u'fullname': u'OpenStax College',
        u'email': u'info@openstaxcollege.org'},
    u'mediaType': u'application/vnd.org.cnx.module',
    u'version': u'8',
    u'googleAnalytics': None,
    u'buyLink': u'http://openstaxcollege.worksmartsuite.com/',
    u'legacy_id':u'm42081',
    u'legacy_version':u'1.8',
    u'history': [
        {
            u'version': u'8',
            u'revised': u'2013-07-31T19:07:24Z',
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
    u'keywords': [
        u'bulk modulus', u'compression', u'deformation', u'force',
        u'Hooke\u2019s law', u'length', u'shear modulus', u'strain', u'stress',
        u'tension', u'Young\u2019s modulus', u'shear deformation',
        u'tensile strength',
        ],
    }

with open(os.path.join(TEST_DATA_DIRECTORY, 'search_results.json'), 'r') as file:
    SEARCH_RESULTS = json.load(file)

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
        version = '7.1'

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
                    u'content[{key}] = {v1} but COLLECTION_METADATA[{key}] = {v2}'.format(
                        key=key, v1=content[key], v2=COLLECTION_METADATA[key]))

        self.maxDiff = 10000
        # Check the tree for accuracy.
        self.assertEqual(content_tree, COLLECTION_JSON_TREE)

    def test_derived_collection(self):
        # Test for retrieving a piece of content.
        uuid = 'a733d0d2-de9b-43f9-8aa9-f0895036899e'
        version = '1.1'

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
        for key in ['parentId','parentTitle','parentAuthors']:
            self.assertEqual(content[key], COLLECTION_DERIVED_METADATA[key],
                    u'content[{key}] = {v1} but COLLECTION_DERIVED_METADATA[{key}] = {v2}'.format(
                        key=key, v1=content[key], v2=COLLECTION_DERIVED_METADATA[key]))

    @db_connect
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
        environ = self._make_environ()
        routing_args = {'ident_hash': '{}@{}'.format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view
        from ..views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

        content_tree = content.pop('tree')

        self.assertEqual(content_tree, {
            u'id': u'{}@{}'.format(uuid, version),
            u'title': u'College Physics',
            u'contents': [
                {
                    u'id': u'subcol',
                    u'title': u'Empty Subcollections',
                    u'contents': [
                        {
                            u'id': u'subcol',
                            u'title': u'empty 1',
                            u'contents': [],
                            },
                        {
                            u'id': u'subcol',
                            u'title': u'empty 2',
                            u'contents': [],
                            },

                        ],
                    },
                {
                    u'id': u'209deb1f-1a46-4369-9e0d-18674cf58a3e@7',
                    u'title': u'Preface',
                    },
                {
                    u'id': u'subcol',
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
        environ = self._make_environ()
        routing_args = {'ident_hash': '{}@{}'.format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view
        from ..views import get_content
        content = get_content(environ, self._start_response)[0]
        content = json.loads(content)

        # History should only include displayed version and older versions
        self.assertEqual(content['history'], [{
            u'version': u'6.1',
            u'revised': u'2013-07-31T19:07:20Z',
            u'changes': 'Updated something',
            u'publisher': {
                u'website': None, u'surname': None,
                u'suffix': None, u'firstname': u'OpenStax College',
                u'title': None, u'othername': None,
                u'id': u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8',
                u'fullname': u'OpenStax College',
                u'email': u'info@openstaxcollege.org'
                },
            }])

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
                    u'content[{key}] = {v1} but MODULE_METADATA[{key}] = {v2}'.format(
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

    def test_content_index_html(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'

        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
                cursor.execute('DELETE FROM module_files')
                # Insert a file for version 4
                cursor.execute('''INSERT INTO files (file) VALUES
                    (%s) RETURNING fileid''', [memoryview('Version 4')])
                fileid = cursor.fetchone()[0]
                cursor.execute('''INSERT INTO module_files
                    (module_ident, fileid, filename, mimetype) VALUES
                    (%s, %s, 'index.cnxml.html', 'text/html')''',
                    [16, fileid])
                # Insert a file for version 5
                cursor.execute('''INSERT INTO files (file) VALUES
                    (%s) RETURNING fileid''', [memoryview('Version 5')])
                fileid = cursor.fetchone()[0]
                cursor.execute('''INSERT INTO module_files
                    (module_ident, fileid, filename, mimetype) VALUES
                    (%s, %s, 'index.cnxml.html', 'text/html')''',
                    [15, fileid])

        def get_content(version):
            # Build the request environment
            environ = self._make_environ()
            routing_args = {'ident_hash': '{}@{}'.format(uuid, version)}
            environ['wsgiorg.routing_args'] = routing_args

            # Call the view
            from ..views import get_content
            content = get_content(environ, self._start_response)[0]
            content = json.loads(content)

            return content.pop('content')

        self.assertEqual(get_content(4), 'Version 4')
        self.assertEqual(get_content(5), 'Version 5')

    def test_content_collection_as_html(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        expected = u"""<html xmlns="http://www.w3.org/1999/xhtml">\n  <body><ul><li><a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@7.1.html">College Physics</a><ul><li><a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7.html">Preface</a></li><li><a>Introduction: The Nature of Science and Physics</a><ul><li><a href="/contents/f3c9ab70-a916-4d8c-9256-42953287b4e9@3.html">Introduction to Science and the Realm of Physics, Physical Quantities, and Units</a></li><li><a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce@4.html">Physics: An Introduction</a></li><li><a href="/contents/c8bdbabc-62b1-4a5f-b291-982ab25756d7@6.html">Physical Quantities and Units</a></li><li><a href="/contents/5152cea8-829a-4aaf-bcc5-c58a416ecb66@7.html">Accuracy, Precision, and Significant Figures</a></li><li><a href="/contents/5838b105-41cd-4c3d-a957-3ac004a48af3@5.html">Approximation</a></li></ul></li><li><a>Further Applications of Newton's Laws: Friction, Drag, and Elasticity</a><ul><li><a href="/contents/24a2ed13-22a6-47d6-97a3-c8aa8d54ac6d@2.html">Introduction: Further Applications of Newton’s Laws</a></li><li><a href="/contents/ea271306-f7f2-46ac-b2ec-1d80ff186a59@5.html">Friction</a></li><li><a href="/contents/26346a42-84b9-48ad-9f6a-62303c16ad41@6.html">Drag Forces</a></li><li><a href="/contents/56f1c5c1-4014-450d-a477-2121e276beca@8.html">Elasticity: Stress and Strain</a></li></ul></li><li><a href="/contents/f6024d8a-1868-44c7-ab65-45419ef54881@3.html">Atomic Masses</a></li><li><a href="/contents/7250386b-14a7-41a2-b8bf-9e9ab872f0dc@2.html">Selected Radioactive Isotopes</a></li><li><a href="/contents/c0a76659-c311-405f-9a99-15c71af39325@5.html">Useful Inførmation</a></li><li><a href="/contents/ae3e18de-638d-4738-b804-dc69cd4db3a3@5.html">Glossary of Key Symbols and Notation</a></li></ul></li></ul></body>\n</html>\n"""

        # Call the view.
        from ..views import get_content_html

        # Check that the view returns the expected html
        resp_body = get_content_html(environ, self._start_response)
        p = HTMLParser.HTMLParser()
        self.assertEqual(p.unescape(resp_body[0]), expected)

    def test_content_module_as_html(self):
        uuid = 'd395b566-5fe3-4428-bcb2-19016e3aa3ce'
        version = '4'

        # Build the request environment.
        environ = self._make_environ()
        routing_args = {'ident_hash': "{}@{}".format(uuid, version)}
        environ['wsgiorg.routing_args'] = routing_args

        # Call the view.
        from ..views import get_content_html

        # Check that the view returns some html
        resp_body = get_content_html(environ, self._start_response)
        self.assertTrue(resp_body[0].startswith('<html'))

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
        version = '7.1'
        type = 'pdf'
        ident_hash = '{}@{}'.format(id, version)
        filename = "{}@{}.{}".format(id, version, type)

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
                         "attached; filename=college-physics-{}.pdf".format(version))
        with open(os.path.join(TEST_DATA_DIRECTORY, 'exports', filename), 'r') as file:
            self.assertEqual(export, file.read())

        # Test exports can access the other exports directory
        id = '56f1c5c1-4014-450d-a477-2121e276beca'
        version = '8'
        ident_hash = '{}@{}'.format(id, version)
        filename = '{}@{}.pdf'.format(id, version)
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash,
                                           'type': 'pdf'
                                           }

        export = get_export(environ, self._start_response)[0]
        headers = self.captured_response['headers']
        headers = {x[0].lower(): x[1] for x in headers}
        self.assertEqual(headers['content-disposition'],
                         "attached; filename=elasticity-stress-and-strain-{}.pdf".format(version))
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

    def test_get_extra_no_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '6.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        output = json.loads(output)
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'downloads': [],
            u'isLatest': False,
            u'canPublish': [u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                            u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                            u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8']
            })

    def test_get_extra_allowable_types(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output)['downloads'], [
            {
                u'format': u'PDF',
                u'filename': u'college-physics-{}.pdf'.format(version),
                u'details': u'PDF file, for viewing content offline and printing.',
                u'path': u'/exports/{}@{}.pdf/college-physics-{}.pdf'.format(
                    id, version, version),
                },
            {
                u'format': u'EPUB',
                u'filename': u'college-physics-{}.epub'.format(version),
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'path': u'/exports/{}@{}.epub/college-physics-{}.epub'.format(
                    id, version, version),
                },
            {
                u'format': u'Offline ZIP',
                u'filename': u'college-physics-{}.zip'.format(version),
                u'details': u'An offline HTML copy of the content.  Also includes XML, included media files, and other support files.',
                u'path': u'/exports/{}@{}.zip/college-physics-{}.zip'.format(
                    id, version, version),
                },
            ])

    def test_extra_downloads_with_legacy_filenames(self):
        # Tests for finding legacy filenames after a module is published from
        # the legacy site
        id = '209deb1f-1a46-4369-9e0d-18674cf58a3e' # m42955
        version = '7' # legacy_version: 1.7
        requested_ident_hash = '{}@{}'.format(id, version)

        # Remove the generated files after the test
        def remove_generated_files():
            for f in glob.glob('{}/exports2/{}@{}.*'.format(
                TEST_DATA_DIRECTORY, id, version)):
                os.unlink(f)
        self.addCleanup(remove_generated_files)

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': requested_ident_hash}

        # Call the target
        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output)['downloads'], [
            {
                u'path': u'/exports/{}@{}.pdf/preface-to-college-physics-7.pdf'
                    .format(id, version),
                u'format': u'PDF',
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'preface-to-college-physics-7.pdf',
                },
            {
                u'path': u'/exports/{}@{}.epub/preface-to-college-physics-7.epub'
                    .format(id, version),
                u'format': u'EPUB',
                u'details': u'Electronic book format file, for viewing on mobile devices.',
                u'filename': u'preface-to-college-physics-7.epub',
                },
            ])

    def test_extra_latest(self):
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output)['isLatest'], True)

        version = '6.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]

        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        self.assertEqual(json.loads(output)['isLatest'], False)

    def test_extra_wo_version(self):
        # Request the extras for a document, but without specifying
        #   the version. The expectation is that this will redirect to the
        #   latest version.
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'
        requested_ident_hash = id
        expected_ident_hash = "{}@{}".format(id, version)

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': requested_ident_hash}

        # Call the target
        from ..views import get_extra
        with self.assertRaises(httpexceptions.HTTPFound) as raiser:
            get_extra(environ, self._start_response)
        exception = raiser.exception
        expected_location = "/extras/{}".format(expected_ident_hash)
        self.assertEqual(exception.headers,
                         [('Location', expected_location)])

    def test_extra_w_utf8_characters(self):
        id = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = '5'
        ident_hash = '{}@{}'.format(id, version)

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': ident_hash}

        # Call the target
        from ..views import get_extra
        output = get_extra(environ, self._start_response)[0]
        self.assertEqual(self.captured_response['status'], '200 OK')
        self.assertEqual(self.captured_response['headers'][0],
                ('Content-type', 'application/json'))
        output = json.loads(output)
        output['canPublish'].sort()
        self.assertEqual(output, {
            u'canPublish': [u'1df3bab1-1dc7-4017-9b3a-960a87e706b1',
                            u'9366c786-e3c8-4960-83d4-aec1269ac5e5',
                            u'e5a07af6-09b9-4b74-aa7a-b7510bee90b8'],
            u'isLatest': True,
            u'downloads': [{
                u'path': u'/exports/{}@{}.pdf/useful-inførmation-5.pdf'
                    .format(id, version),
                u'format': u'PDF',
                u'details': u'PDF file, for viewing content offline and printing.',
                u'filename': u'useful-inførmation-5.pdf',
                }],
            })

    def test_extra_not_found(self):
        # Test version not found
        id = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '1.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        from ..views import get_extra
        self.assertRaises(httpexceptions.HTTPNotFound, get_extra, environ,
                self._start_response)

        # Test id not found
        id = 'c694e5cc-47bd-41a4-b319-030647d93440'
        version = '1.1'

        # Build the request
        environ = self._make_environ()
        environ['wsgiorg.routing_args'] = {'ident_hash': '{}@{}'.format(id, version)}

        self.assertRaises(httpexceptions.HTTPNotFound, get_extra, environ,
                self._start_response)

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
        self.maxDiff = None
        for i in results:
            self.assertEqual(results[i], SEARCH_RESULTS[i])

    def test_search_title_w_whitespace(self):
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q=title:"   preface  to college   physics "'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(results['query'], {
            u'limits': [{u'tag': u'title', u'value': u'preface to college physics'}],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_only_subject(self):
        # From the Content page, we have a list of subjects (tags),
        # they link to the search page like: /search?q=subject:"Arts"

        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q=subject:"Science and Technology"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(results['query'], {
            u'limits': [{u'tag': u'subject', u'value': u'Science and Technology'}],
            u'sort': []})
        self.assertEqual(results['results']['total'], 7)

    def test_search_with_subject(self):
        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q=title:"college physics" subject:"Science and Technology"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(results['query'], {
            u'limits': [
                {u'tag': u'title', u'value': u'college physics'},
                {u'tag': u'subject', u'value': 'Science and Technology'},
                ],
            u'sort': []})
        self.assertEqual(results['results']['total'], 1)

    def test_search_highlight_abstract(self):
        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q="college physics"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(results['results']['items'][0]['summarySnippet'],
                'algebra-based, two-semester <b>college</b> <b>physics</b> book '
                'is grounded with real-world examples, illustrations, and '
                'explanations to help students grasp key, fundamental '
                '<b>physics</b> concepts. This online, fully editable and '
                'customizable title includes learning objectives, concept '
                'questions, links to labs and simulations, and ample practice '
                'opportunities to solve traditional <b>physics</b> application '
                'problems. ')
        self.assertEqual(results['results']['items'][1]['summarySnippet'], None)
        self.assertEqual(results['results']['items'][2]['summarySnippet'],
                'algebra-based, two-semester <b>college</b> <b>physics</b> book '
                'is grounded with real-world examples, illustrations, and '
                'explanations to help students grasp key, fundamental '
                '<b>physics</b> concepts. This online, fully editable and '
                'customizable title includes learning objectives, concept '
                'questions, links to labs and simulations, and ample practice '
                'opportunities to solve traditional <b>physics</b> application '
                'problems. ')

        # Test for no highlighting on specific field queries.
        environ['QUERY_STRING'] = 'q=title:"college physics"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))
        results = json.loads(results)

        self.assertEqual(results['results']['items'][0]['summarySnippet'],
                ' This introductory, algebra-based, two-semester college physics '
                'book is grounded with real-world examples, illustrations, and '
                'explanations to help students grasp key, fundamental physics '
                'concepts. This online, fully editable and customizable title '
                'includes learning objectives, concept questions, links to labs '
                'and simulations, and ample practice opportunities to solve '
                'traditional')
        self.assertEqual(results['results']['items'][1]['summarySnippet'],
                ' This introductory, algebra-based, two-semester college physics '
                'book is grounded with real-world examples, illustrations, and '
                'explanations to help students grasp key, fundamental physics '
                'concepts. This online, fully editable and customizable title '
                'includes learning objectives, concept questions, links to labs '
                'and simulations, and ample practice opportunities to solve '
                'traditional')
        self.assertEqual(results['results']['items'][2]['summarySnippet'], None)

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
                u'limits': [],
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
                u'limits': [],
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

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': u'你好'}],
                u'sort': [],
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
                        {u'name': u'Collection',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Module',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    }, 
                },
            }
        self.assertEqual(json.loads(results), expected)

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

        expected = {
            u'query': {
                u'limits': [{u'tag': u'text', u'value': ur":\.+'?"}],
                u'sort': [],
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
                        {u'name': u'Collection',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Module',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    }, 
                },
            }
        self.assertEqual(json.loads(results), expected)

    def test_search_unbalanced_quotes(self):
        environ = self._make_environ()
        environ['QUERY_STRING'] = r'q="a phrase" "something else sort:pubDate author:"first last"'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        expected = {
            u'query': {
                u'limits': [
                    {u'tag': u'text', u'value': u'a phrase'},
                    {u'tag': u'text', u'value': u'something else'},
                    {u'tag': u'author', u'value': 'first last'},
                    ],
                u'sort': [u'pubDate'],
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
                        {u'name': u'Collection',
                         u'id': u'application/vnd.org.cnx.collection'},
                        {u'name': u'Module',
                         u'id': u'application/vnd.org.cnx.module'},
                        ],
                    }, 
                },
            }
        self.assertEqual(json.loads(results), expected)

    def test_search_type_page_or_module(self):
        # Test searching "page"

        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q=title:"college physics" type:page'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        results = json.loads(results)
        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'page'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'Module')

        # Test searching "module"

        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = r'q="college physics" type:module'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        results = json.loads(results)
        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'module'})
        self.assertEqual(results['results']['total'], 1)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'Module')

    def test_search_type_book_or_collection(self):
        # Test searching "book"

        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = 'q=title:physics type:book'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        results = json.loads(results)
        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'book'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'Collection')

        # Test searching "collection"

        # Build the request
        environ = self._make_environ()
        environ['QUERY_STRING'] = r'q=title:physics type:collection'

        from ..views import search
        results = search(environ, self._start_response)[0]
        status = self.captured_response['status']
        headers = self.captured_response['headers']

        self.assertEqual(status, '200 OK')
        self.assertEqual(headers[0], ('Content-type', 'application/json'))

        results = json.loads(results)
        self.assertEqual(results['query']['limits'][-1],
                         {u'tag': u'type', u'value': u'collection'})
        self.assertEqual(results['results']['total'], 2)
        self.assertEqual(results['results']['items'][0]['mediaType'],
                         'Collection')


    def test_extras(self):
        # Build the request
        environ = self._make_environ()

        # Call the view
        from ..views import extras
        metadata = extras(environ, self._start_response)[0]
        metadata = json.loads(metadata)
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
                          },
                         ]
            })


    def test_sitemap(self):
        # Build the request
        environ = self._make_environ()

        # Call the view
        from ..views import sitemap
        sitemap = sitemap(environ, self._start_response)[0]
        with open(os.path.join(TEST_DATA_DIRECTORY, 'sitemap.xml'), 'r') as file:
            self.assertMultiLineEqual(sitemap, file.read())
