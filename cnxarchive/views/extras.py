# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Extras Views."""
import os
import json
import logging
from datetime import datetime, timedelta
from re import compile

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from .. import cache
from ..database import SQL, get_module_can_publish
from ..utils import fromtimestamp, split_ident_hash

from .views_helpers import get_latest_version
from .exports import get_export_allowable_types

logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


def is_latest(id, version):
    """Determine if this is the latest version of this content."""
    return get_latest_version(id) == version


def _get_available_languages_and_count(cursor):
    """Return a list of available language and its count"""
    cursor.execute(SQL['get-available-languages-and-count'])
    return cursor.fetchall()


def _get_subject_list(cursor):
    """Return all subjects (tags) in the database except "internal" scheme."""
    subject = None
    last_tagid = None
    cursor.execute(SQL['get-subject-list'])
    for s in cursor.fetchall():
        tagid, tagname, portal_type, count = s

        if tagid != last_tagid:
            # It's a new subject, create a new dict and initialize count
            if subject:
                yield subject
            subject = {'id': tagid,
                       'name': tagname,
                       'count': {'module': 0, 'collection': 0}, }
            last_tagid = tagid

        if tagid == last_tagid and portal_type:
            # Just need to update the count
            subject['count'][portal_type.lower()] = count

    if subject:
        yield subject


def _get_featured_links(cursor):
    """Return featured books for the front page."""
    cursor.execute(SQL['get-featured-links'])
    return [i[0] for i in cursor.fetchall()]


def _get_service_state_messages(cursor):
    """Return a list of service messages."""
    cursor.execute(SQL['get-service-state-messages'])
    return [i[0] for i in cursor.fetchall()]


def _get_licenses(cursor):
    """Return a list of license info."""
    cursor.execute(SQL['get-license-info-as-json'])
    return [json_row[0] for json_row in cursor.fetchall()]


# ######### #
#   Views   #
# ######### #


@view_config(route_name='content-extras', request_method='GET')
def get_extra(request):
    """Return information about a module / collection that cannot be cached."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    id, version = split_ident_hash(args['ident_hash'])
    results = {}

    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            results['downloads'] = \
                list(get_export_allowable_types(cursor, exports_dirs,
                                                id, version))
            results['isLatest'] = is_latest(id, version)
            results['canPublish'] = get_module_can_publish(cursor, id)

    resp = request.response
    resp.content_type = 'application/json'
    resp.body = json.dumps(results)
    return resp


@view_config(route_name='extras', request_method='GET')
def extras(request):
    """Return a dict with archive metadata for webview."""
    settings = get_current_registry().settings
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
        with db_connection.cursor() as cursor:
            metadata = {
                'languages_and_count': _get_available_languages_and_count(
                    cursor),
                'subjects': list(_get_subject_list(cursor)),
                'featuredLinks': _get_featured_links(cursor),
                'messages': _get_service_state_messages(cursor),
                'licenses': _get_licenses(cursor),
                }

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'application/json'
    resp.body = json.dumps(metadata)
    return resp
