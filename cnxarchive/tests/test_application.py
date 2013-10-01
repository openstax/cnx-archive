# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest
from wsgiref.util import setup_testing_defaults


class RoutingTest(unittest.TestCase):

    def test_add_route_w_fq_import(self):
        # Check that a route can be added.
        from ..views import get_content
        route_func = get_content
        path = "/contents/{ident_hash}"

        from .. import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        self.assertEqual(controller, get_content)

    def test_add_route_w_import_str(self):
        # Check that a route can be added.
        route_func = 'cnxarchive.views:get_content'
        path = "/contents/{ident_hash}"

        from .. import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        from ..views import get_content
        self.assertEqual(controller, get_content)

    def test_route(self):
        # Check that we can route to a view, not that the route parses
        #   the path information.
        from .. import Application
        app = Application()

        path_one = "/contents/{ident_hash}"
        view_one = 'cnxarchive.views:get_content'
        app.add_route(path_one, view_one)
        path_two = "/resources/{id}"
        view_two = 'cnxarchive.views:get_resource'
        app.add_route(path_two, view_two)

        id = '1a2b3c4d5678'
        environ = {'PATH_INFO': '/resources/{}'.format(id)}
        setup_testing_defaults(environ)
        controller = app.route(environ)

        from ..views import get_resource
        self.assertEqual(controller, get_resource)
        self.assertEqual(environ['wsgiorg.routing_args'],
                         {'id': id})


class CORSTestCase(unittest.TestCase):
    """Tests for correctly enabling CORS on the server
    """

    def start_response(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def controller(self, environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return ['hello']

    def test_get(self):
        # We should have "Access-Control-Allow-Origin: *" in
        # the headers
        from .. import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'GET',
                'PATH_INFO': '/',
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
            ]))
        self.assertEqual(self.kwargs, {})

    def test_options(self):
        # We should have "Access-Control-Allow-Origin: *" in the headers for
        # preflighted requests
        from .. import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'OPTIONS',
                'PATH_INFO': '/',
                'HTTP_ACCESS_CONTROL_REQUEST_HEADERS':
                'origin, accept-encoding, accept-language, cache-control'
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
            ('Access-Control-Allow-Headers',
                'origin, accept-encoding, accept-language, cache-control'),
            ]))
        self.assertEqual(self.kwargs, {})

    def test_post(self):
        # We should not have "Access-Control-Allow-Origin: *" in
        # the headers
        from .. import Application
        app = Application()
        app.add_route('/', self.controller)
        environ = {
                'REQUEST_METHOD': 'POST',
                'PATH_INFO': '/',
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ]))
        self.assertEqual(self.kwargs, {})
