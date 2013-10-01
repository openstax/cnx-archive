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
