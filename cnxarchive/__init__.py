# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Document and collection archive web application."""
import re
from .utils import import_function, template_to_regex


_settings = None

def get_settings():
    """Retrieve the application settings"""
    global _settings
    return _settings
def _set_settings(settings):
    """Assign the application settings."""
    global _settings
    _settings = settings
def _setting_to_bool(value):
    value = value.lower()
    if value.startswith('t') or value == '1':
        return True
    return False


def not_found(environ, start_response):
    """404 Not Found"""
    start_response('404 Not Found', headers=[('Content-type', 'text/plain')])
    return ["Not Found"]


class Application:
    """WSGI application"""
    # Derived from a WebOb routing example.

    def __init__(self):
        self._routes = []

    def add_route(self, template, controller, **vars):
        """Adds a route to the application. ``template`` is a route template
        writen in a simple replacement DSL (see ``template_to_regex``).
        ``controller`` is the a string referrence to the controller function
        (see ``load_controller`` for syntax details). Lastely, ``vars`` are
        keyword arguments to pass into the routing arguments as constants.
        """
        if isinstance(controller, basestring):
            controller = import_function(controller)
        self._routes.append((re.compile(template_to_regex(template)),
                             controller,
                             vars))

    def route(self, environ):
        for regex, controller, vars in self._routes:
            match = regex.match(environ['PATH_INFO'])
            if match:
                environ['wsgiorg.routing_args'] = match.groupdict()
                environ['wsgiorg.routing_args'].update(vars)
                return controller
        return None

    def __call__(self, environ, start_response):
        controller = self.route(environ)
        if controller is not None:
            return controller(environ, start_response)
        return not_found(environ, start_response)


def main(global_config, **settings):
    """Main WSGI application factory."""
    _set_settings(settings)
    app = Application()
    app.add_route('/contents/{ident_hash}', 'cnxarchive.views:get_content')
    app.add_route('/resources/{id}', 'cnxarchive.views:get_resource')
    dev_mode = _setting_to_bool(settings.get('dev-mode', False))
    if dev_mode:
        if not settings.get('exports-directory', None):
            raise ValueError("Missing exports-directory configuration setting.")
        app.add_route('/exports/{ident_hash}/{type}', 'cnxarchive.views:get_export')
    return app
