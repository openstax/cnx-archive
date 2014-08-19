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

from .. import DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS


def faux_view(environ, start_response):
    args = ', '.join(["{}={}".format(k,v)
                      for k,v in environ['wsgiorg.routing_args']])
    status = "200 OK"
    headers = [('Content-type', 'text/plain',)]
    start_response(status, headers)
    return [args]

def faux_view_one(environ, start_response):
    return faux_view(environ, start_response)

def faux_view_two(environ, start_response):
    return faux_view(environ, start_response)


class RoutingTest(unittest.TestCase):

    def test_add_route_w_fq_import(self):
        # Check that a route can be added.
        route_func = faux_view
        path = "/contents/{ident_hash}"

        from .. import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        self.assertEqual(controller, route_func)

    def test_add_route_w_import_str(self):
        # Check that a route can be added.
        route_func = 'cnxarchive.tests.test_application:faux_view'
        path = "/contents/{ident_hash}"

        from .. import Application
        app = Application()
        app.add_route(path, route_func)

        environ = {'PATH_INFO': "/contents/1234abcd"}
        controller = app.route(environ)
        from ..views import get_content
        self.assertEqual(controller, faux_view)

    def test_route(self):
        # Check that we can route to a view, not that the route parses
        #   the path information.
        from .. import Application
        app = Application()

        path_one = "/a/{b}/{c}"
        view_one = 'cnxarchive.tests.test_application:faux_view_one'
        app.add_route(path_one, view_one)
        path_two = "/x/{y}/{z}"
        view_two = 'cnxarchive.tests.test_application:faux_view_two'
        app.add_route(path_two, view_two)

        y = 'smoo'
        z = 'oog'
        environ = {'PATH_INFO': path_two.format(y=y, z=z)}
        setup_testing_defaults(environ)
        controller = app.route(environ)

        self.assertEqual(controller, faux_view_two)
        self.assertEqual(environ['wsgiorg.routing_args'],
                         {'y': y, 'z': z})

    def test_route_w_custom_regexp(self):
        # routes with more specific regexp should be added first
        route_func1 = faux_view_one
        path1 = '/contents/{ident_hash:.*}.html'
        route_func2 = faux_view_two
        path2 = '/contents/{ident_hash:.*}.json'
        # the most general regexp should be added last
        # otherwise it'll capture all the requests
        route_func3 = faux_view
        path3 = '/contents/{ident_hash}'

        from .. import Application
        app = Application()
        app.add_route(path1, route_func1)
        app.add_route(path2, route_func2)
        app.add_route(path3, route_func3)

        environ = {'PATH_INFO': '/contents/1234abcd'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func3)

        environ = {'PATH_INFO': '/contents/1234abcd@1'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func3)

        environ = {'PATH_INFO': '/contents/1234abcd@1.1'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func3)

        environ = {'PATH_INFO': '/contents/1234abcd.html'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func1)

        environ = {'PATH_INFO': '/contents/1234abcd@1.html'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func1)

        environ = {'PATH_INFO': '/contents/1234abcd@1.1.html'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func1)

        environ = {'PATH_INFO': '/contents/1234abcd.json'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func2)

        environ = {'PATH_INFO': '/contents/1234abcd@1.json'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func2)

        environ = {'PATH_INFO': '/contents/1234abcd@1.1.json'}
        controller = app.route(environ)
        self.assertEqual(controller, route_func2)


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
            ('Access-Control-Allow-Headers',
             ','.join(DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS)),
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
                'origin, accept-encoding, accept-language, something-special'
                }
        app(environ, self.start_response)
        self.assertEqual(self.args, ('200 OK', [
            ('Content-type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
            ('Access-Control-Allow-Headers',
             ','.join(DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS)),
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
