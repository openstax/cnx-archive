# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Pyramid events, extended for CORS."""

from pyramid.events import NewRequest

from . import DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS


def add_cors_headers(request, response):
    """Add cors headers needed for web app implementation."""
    response.headerlist.append(('Access-Control-Allow-Origin', '*'))
    response.headerlist.append(
        ('Access-Control-Allow-Methods', 'GET, OPTIONS'))
    response.headerlist.append(
        ('Access-Control-Allow-Headers',
         ','.join(DEFAULT_ACCESS_CONTROL_ALLOW_HEADERS)))


def new_request_subscriber(event):
    """Subscribe to request creation, to add cors headers."""
    request = event.request
    request.add_response_callback(add_cors_headers)


def main(config):
    """Do it."""
    config.add_subscriber(new_request_subscriber, NewRequest)
