# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Document and collection archive web application."""
import os
import re
import logging
from logging.config import fileConfig as load_logging_configuration

from . import httpexceptions
from .utils import import_function, template_to_regex


here = os.path.abspath(os.path.dirname(__file__))
DEFAULT_LOGGING_CONFIG_FILEPATH = os.path.join(here, 'default-logging.ini')

logger = logging.getLogger('cnxarchive')
_settings = None

DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS = [
    'origin',
    'dnt',
    'accept-encoding',
    'accept-language',
    'keep-alive',
    'user-agent',
    'x-requested-with',
    'if-modified-since',
    'cache-control',
    'content-type',
    ]

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


class Application:
    """WSGI application"""
    # Derived from a WebOb routing example.

    def __init__(self):
        self._routes = []

    def add_route(self, template, controller, **vars):
        """Adds a route to the application. ``template`` is a route template
        writen in a simple replacement DSL (see ``template_to_regex``).
        ``controller`` is the a string reference to the controller function
        (see ``load_controller`` for syntax details). Lastly, ``vars`` are
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

    def add_cors(self, environ, start_response):
        """A start_response wrapper to add CORS header to GET requests
        """
        def r(status, headers, *args, **kwargs):
            headers.append(('Access-Control-Allow-Origin', '*'))
            headers.append(('Access-Control-Allow-Methods', 'GET, OPTIONS'))
            headers.append(('Access-Control-Allow-Headers',
                            ','.join(DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS)))
            start_response(status, headers, *args, **kwargs)
        return r

    def log_request(self, environ):
        path = environ['PATH_INFO']
        if environ.get('QUERY_STRING'):
            path = "{}?{}".format(path, environ['QUERY_STRING'])
        message = "{} - {}".format(environ['REQUEST_METHOD'], path)
        logger.info(message)

    def __call__(self, environ, start_response):
        self.log_request(environ)
        controller = self.route(environ)
        if environ.get('REQUEST_METHOD', '') in ['GET', 'OPTIONS']:
            start_response = self.add_cors(environ, start_response)
        if controller is not None:
            try:
                return controller(environ, start_response)
            except httpexceptions.HTTPException as exc:
                return exc(environ, start_response)
            except:
                logger.exception("Unknown exception")
                server_error = httpexceptions.HTTPInternalServerError()
                return server_error(environ, start_response)
        return httpexceptions.HTTPNotFound()(environ, start_response)


def main(global_config, **settings):
    """Main WSGI application factory."""
    _set_settings(settings)
    # Initialize logging
    logging_config_filepath = settings.get('logging-configuration-filepath',
                                           DEFAULT_LOGGING_CONFIG_FILEPATH)
    load_logging_configuration(logging_config_filepath)

    app = Application()
    app.add_route('/contents/{ident_hash:([^:/]*)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}.html', 'cnxarchive.views:get_content_html')
    app.add_route('/contents/{ident_hash:([^:/]*)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}.json', 'cnxarchive.views:get_content_json')
    # app.add_route('/contents/{ident_hash}.snippet', 'cnxarchive.views:get_content_snippet')
    app.add_route('/contents/{ident_hash:([^:/]*)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}', 'cnxarchive.views:get_content')
    app.add_route('/resources/{hash}{ignore:(/.*)?}', 'cnxarchive.views:get_resource')
    app.add_route('/exports/{ident_hash}.{type}{ignore:(/.*)?}', 'cnxarchive.views:get_export')
    app.add_route('/extras/{ident_hash}', 'cnxarchive.views:get_extra')
    app.add_route('/search', 'cnxarchive.views:search')
    app.add_route('/extras', 'cnxarchive.views:extras')
    app.add_route('/sitemap.xml', 'cnxarchive.views:sitemap')
    app.add_route('/content/{objid}{ignore:(/)?}', 'cnxarchive.views:redirect_legacy_content')
    app.add_route('/content/{objid}/latest{ignore:(/)?}{filename:(.+)?}', 'cnxarchive.views:redirect_legacy_content')
    app.add_route('/content/{objid}/{objver}{ignore:(/)?}{filename:(.+)?}', 'cnxarchive.views:redirect_legacy_content')

    mandatory_settings = ['exports-directories', 'exports-allowable-types']
    for setting in mandatory_settings:
        if not settings.get(setting, None):
            raise ValueError('Missing {} configuration setting.'.format(setting))

    return app
