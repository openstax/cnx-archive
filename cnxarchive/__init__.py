# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Document and collection archive web application."""
import os
import warnings

from pyramid.config import Configurator

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


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


def find_migrations_directory():
    """Finds and returns the location of the database migrations directory.
    This function is used from a setuptools entry-point for db-migrator.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, 'sql/migrations')


def declare_api_routes(config):
    """Declare routes, with a custom pregenerator."""
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

    add_route('content', '/contents/{ident_hash:([^:/@.]+(@[0-9.]*[0-9]+)?)}{separator:(:?)}{page_ident_hash:([^:/@.]+(@[0-9.]*[0-9]+)?)?}{ignore:(/[^/.]*?/?)?}{ext:([.](html|json))?}')  # noqa cnxarchive.views:get_content
    add_route('resource', '/resources/{hash}{ignore:(/.*)?}')  # noqa cnxarchive.views:get_resource
    add_route('export', '/exports/{ident_hash}.{type}{ignore:(/.*)?}')  # noqa cnxarchive.views:get_export
    add_route('extras', '/extras{key:(/(featured|messages|licenses|subjects|languages))?}')  # noqa cnxarchive.views:extras
    add_route('content-extras', '/extras/{ident_hash:([^:/@.]+(@[0-9.]*[0-9]+)?)}{separator:(:?)}{page_ident_hash:([^:/@.]+(@[0-9.]*[0-9]+)?)?}')  # noqa cnxarchive.views:get_extra
    add_route('search', '/search')  # cnxarchive.views:search
    add_route('in-book-search', '/search/{ident_hash:([^:/]+)}')  # noqa cnxarchive.views:in-book-search
    add_route('in-book-search-page', '/search/{ident_hash:([^:/]+)}:{page_ident_hash}')  # noqa cnxarchive.views:in_book_search_highlighted_results
    add_route('sitemap-index', '/sitemap_index.xml')  # noqa cnxarchive.views:sitemap
    add_route('sitemap', '/sitemap-{from_id}.xml')  # noqa cnxarchive.views:sitemap
    add_route('robots', '/robots.txt')  # noqa cnxarchive.views:robots
    add_route('legacy-redirect', '/content/{objid}{ignore:(/)?}')  # noqa cnxarchive.views:redirect_legacy_content
    add_route('legacy-redirect-latest', '/content/{objid}/latest{ignore:(/)?}{filename:(.+)?}')  # noqa cnxarchive.views:redirect_legacy_content
    add_route('legacy-redirect-w-version', '/content/{objid}/{objver}{ignore:(/)?}{filename:(.+)?}')  # noqa cnxarchive.views:redirect_legacy_content
    add_route('recent', '/feeds/recent.rss')  # cnxarchive.views:recent
    add_route('oai', '/feeds/oai')  # cnxarchive.views:oai
    add_route('xpath', '/xpath.html')  # cnxarchive.views.xpath
    add_route('xpath-json', '/xpath.json')  # cnxarchive.views.xpath


def declare_type_info(config):
    """Lookup type info from app configuration."""
    settings = config.registry.settings
    settings['_type_info'] = []
    for line in settings['exports-allowable-types'].splitlines():
        if not line.strip():
            continue
        type_name, type_info = line.strip().split(':', 1)
        type_info = type_info.split(',', 3)
        settings['_type_info'].append((type_name, {
            'type_name': type_name,
            'file_extension': type_info[0],
            'mimetype': type_info[1],
            'user_friendly_name': type_info[2],
            'description': type_info[3],
            }))


def initialize_sentry_integration():  # pragma: no cover
    """\
    Used to optionally initialize the Sentry service with this app.
    See https://docs.sentry.io/platforms/python/pyramid/

    """
    # This function is not under coverage because it is boilerplate
    # from the Sentry documentation.
    try:
        import sentry_sdk
        from sentry_sdk.integrations.pyramid import PyramidIntegration
    except ImportError:
        warnings.warn(
            "Sentry is not configured because the Sentry SDK "
            "(sentry_sdk package) is not installed",
            UserWarning,
        )
        return  # bail out early

    try:
        dsn = os.environ['SENTRY_DSN']
    except KeyError:
        warnings.warn(
            "Sentry is not configured because SENTRY_DSN "
            "was not supplied.",
            UserWarning,
        )
    else:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[PyramidIntegration()],
        )


def main(global_config, **settings):
    """Main WSGI application factory."""
    initialize_sentry_integration()
    config = Configurator(settings=settings)
    declare_api_routes(config)
    declare_type_info(config)

    # allowing the pyramid templates to render rss and xml
    config.include('pyramid_jinja2')
    config.add_jinja2_renderer('.html')
    config.add_jinja2_renderer('.rss')
    config.add_jinja2_renderer('.xml')

    mandatory_settings = ['exports-directories', 'exports-allowable-types']
    for setting in mandatory_settings:
        if not settings.get(setting, None):
            raise ValueError('Missing {} config setting.'.format(setting))

    config.scan(ignore='.tests')
    config.include('cnxarchive.events.main')

    config.add_tween('cnxarchive.tweens.conditional_http_tween_factory')

    return config.make_wsgi_app()
