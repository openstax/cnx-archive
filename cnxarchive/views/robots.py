# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""View robots.txt page."""
from pyramid.view import view_config


@view_config(route_name='robots', request_method='GET',
             http_cache=(86400, {'public': True}))
def robots(request):
    """Return a simple "don't index me" robots.txt file."""

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'text/plain'
    resp.body = """
User-Agent: *
Disallow: /
"""
    return resp
