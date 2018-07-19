# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, 2015 Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest
from pyramid.testing import DummyRequest


class RoutingTestCase(unittest.TestCase):

    def test_route_setup(self):
        from .testing import integration_test_settings
        settings = integration_test_settings()

        from .. import main
        app = main({}, **settings)

        tests = {
            # controller name: (path, routing args)
            'content': (
                ('/contents/abcd-1234.html', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '',
                    'ext': '.html',
                    }),
                ('/contents/abcd-1234/title.html', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '/title',
                    'ext': '.html',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678@3.html', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '',
                    'ext': '.html',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678@3/ignore.html', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '/ignore',
                    'ext': '.html',
                    }),
                ('/contents/abcd-1234.json', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '',
                    'ext': '.json',
                    }),
                ('/contents/abcd-1234/title.json', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '/title',
                    'ext': '.json',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678@3.json', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '',
                    'ext': '.json',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678@3/ignore.json', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '/ignore',
                    'ext': '.json',
                    }),
                ('/contents/abcd-1234', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '',
                    'ext': '',
                    }),
                ('/contents/abcd-1234/', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '/',
                    'ext': '',
                    }),
                ('/contents/abcd-1234/title', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '/title',
                    'ext': '',
                    }),
                ('/contents/abcd-1234/title/', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': '',
                    'separator': '',
                    'ignore': '/title/',
                    'ext': '',
                    }),
                ('/contents/abcd-1234:efgh-5678@3/ignore', {
                    'ident_hash': 'abcd-1234',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '/ignore',
                    'ext': '',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678',
                    'separator': ':',
                    'ignore': '',
                    'ext': '',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678/', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678',
                    'separator': ':',
                    'ignore': '/',
                    'ext': '',
                    }),
                ('/contents/abcd-1234@1.2:efgh-5678@3/ignore', {
                    'ident_hash': 'abcd-1234@1.2',
                    'page_ident_hash': 'efgh-5678@3',
                    'separator': ':',
                    'ignore': '/ignore',
                    'ext': '',
                    })
                ),
            'resource': (
                ('/resources/abcd1234', {
                    'hash': 'abcd1234',
                    'ignore': '',
                    }),
                ('/resources/abcd1234/', {
                    'hash': 'abcd1234',
                    'ignore': '/',
                    }),
                ('/resources/abcd1234/picture.jpg', {
                    'hash': 'abcd1234',
                    'ignore': '/picture.jpg',
                    }),
                ),
            'export': (
                ('/exports/abcd-1234.pdf', {
                    'ident_hash': 'abcd-1234',
                    'type': 'pdf',
                    'ignore': '',
                    }),
                ('/exports/abcd-1234.pdf/title.pdf', {
                    'ident_hash': 'abcd-1234',
                    'type': 'pdf',
                    'ignore': '/title.pdf',
                    }),
                ),
            'extras': (
                ('/extras', {
                    'key': ''
                    }),
                ('/extras/featured', {
                    'key': '/featured'
                    }),
                ('/extras/messages', {
                    'key': '/messages'
                    }),
                ('/extras/licenses', {
                    'key': '/licenses'
                    }),
                ('/extras/subjects', {
                    'key': '/subjects'
                    }),
                ('/extras/languages', {
                    'key': '/languages'
                    }),
                ),
            'content-extras': (
                ('/extras/abcd@1234', {
                    'ident_hash': 'abcd@1234',
                    'page_ident_hash': '',
                    'separator': ''
                    }),
                ),
            'content-extras': (
                ('/extras/abcd@1234:efgh@5678', {
                    'ident_hash': 'abcd@1234',
                    'page_ident_hash': 'efgh@5678',
                    'separator': ':'
                    }),
                ),
            'search': (
                ('/search', {}),
                ),
            'sitemap': (
                ('/sitemap-1.xml', {
                    'from_id': '1',
                    }),
                ),
            'sitemap-index': (
                ('/sitemap_index.xml', {}),
                ),
            'legacy-redirect': (
                ('/content/m12345', {
                    'objid': 'm12345',
                    'ignore': '',
                    }),
                ('/content/m12345/', {
                    'objid': 'm12345',
                    'ignore': '/',
                    }),
                ),
            'legacy-redirect-w-version': (
                ('/content/m12345/1.2', {
                    'objid': 'm12345',
                    'objver': '1.2',
                    'ignore': '',
                    'filename': '',
                    }),
                ('/content/m12345/1.2/', {
                    'objid': 'm12345',
                    'objver': '1.2',
                    'ignore': '/',
                    'filename': '',
                    }),
                ('/content/m12345/1.2/picture.jpg', {
                    'objid': 'm12345',
                    'objver': '1.2',
                    'ignore': '/',
                    'filename': 'picture.jpg',
                    }),
                ),
            'legacy-redirect-latest': (
                ('/content/m12345/latest', {
                    'objid': 'm12345',
                    'ignore': '',
                    'filename': '',
                    }),
                ('/content/m12345/latest/', {
                    'objid': 'm12345',
                    'ignore': '/',
                    'filename': '',
                    }),
                ),
            None: (
                ('/extras/', None),
                ('/contents', None),
                ('/contents/', None),
                ),
            }

        for controller_name, args in tests.items():
            for path, routing_args in args:
                req = DummyRequest(environ={'PATH_INFO': path})
                routemap = app.routes_mapper(req)
                route = routemap['route']
                routename = getattr(route, 'name', None)
                self.assertEqual(routename, controller_name)
                self.assertEqual(routemap['match'], routing_args)
