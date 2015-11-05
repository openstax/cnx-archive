# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Document and collection archive web application."""
from __future__ import unicode_literals
import sys

from pyramid.config import Configurator


# XXX (25-Sep-2015) This should probably go somewhere?
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
IS_PY2 = sys.version_info.major == 2


def declare_api_routes(config):
    """Declaration of routing"""
    # The pregenerator makes sure we can generate a path using
    # request.route_path even if we don't have all the variables.
    #
    # For example, instead of having to do this:
    #     request.route_path('resource', hash=hash, ignore='')
    # it's possible to do this:
    #     request.route_path('resource', hash=hash)
    def pregenerator(path):
        # find all the variables in the path
        variables = [(s.split(':')[0], '') for s in path.split('{')[1:]]

        def wrapper(request, elements, kwargs):
            modified_kwargs = dict(variables)
            modified_kwargs.update(kwargs)
            return elements, modified_kwargs
        return wrapper

    def add_route(name, path, *args, **kwargs):
        return config.add_route(name, path, *args,
                                pregenerator=pregenerator(path), **kwargs)

    add_route('content-html', '/contents/{ident_hash:([^:/]*)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}.html')  # noqa cnxarchive.views:get_content_html
    add_route('content-json', '/contents/{ident_hash:([^:/]*)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}.json')  # noqa cnxarchive.views:get_content_json
    add_route('content', '/contents/{ident_hash:([^:/]+)}{separator:(:?)}{page_ident_hash:([^/]*)}{ignore:(/.*)?}')  # noqa cnxarchive.views:get_content
    add_route('resource', '/resources/{hash}{ignore:(/.*)?}')  # noqa cnxarchive.views:get_resource
    add_route('export', '/exports/{ident_hash}.{type}{ignore:(/.*)?}')  # noqa cnxarchive.views:get_export
    add_route('content-extras', '/extras/{ident_hash}')  # noqa cnxarchive.views:get_extra
    add_route('search', '/search')  # cnxarchive.views:search
    add_route('in-book-search', '/search/{ident_hash}')  # noqa cnxarchive.views:in-book-search
    add_route('in-book-search-page', '/search/{ident_hash}/{page_ident_hash}')  # noqa cnxarchive.views:in_book_search_highlighted_results
    add_route('extras', '/extras')  # cnxarchive.views:extras
    add_route('sitemap', '/sitemap.xml')  # cnxarchive.views:sitemap
    add_route('robots', '/robots.txt')  # cnxarchive.views:robots
    add_route('legacy-redirect', '/content/{objid}{ignore:(/)?}')  # noqa cnxarchive.views:redirect_legacy_content
    add_route('legacy-redirect-latest', '/content/{objid}/latest{ignore:(/)?}{filename:(.+)?}')  # noqa cnxarchive.views:redirect_legacy_content
    add_route('legacy-redirect-w-version', '/content/{objid}/{objver}{ignore:(/)?}{filename:(.+)?}')  # noqa cnxarchive.views:redirect_legacy_content


def main(global_config, **settings):
    """Main WSGI application factory."""
    config = Configurator(settings=settings)
    declare_api_routes(config)

    mandatory_settings = ['exports-directories', 'exports-allowable-types']
    for setting in mandatory_settings:
        if not settings.get(setting, None):
            raise ValueError('Missing {} config setting.'.format(setting))

    if IS_PY2:
        config.scan(ignore=b'.tests')
    else:
        config.scan(ignore='.tests')
    config.include('cnxarchive.events.main')
    return config.make_wsgi_app()
