# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Robots Views."""
import os
import json
import logging
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
from cnxepub.models import flatten_tree_to_ident_hashes
from lxml import etree
from pytz import timezone
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import cache
from ..robots import Robots
from ..utils import fromtimestamp

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']


# #################### #
#   Helper functions   #
# #################### #


def html_date(datetime):
    """
    Return the HTTP-date format of python's datetime time.

    Based on:
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    """
    return datetime.strftime("%a, %d %b %Y %X %Z")


# ######### #
#   Views   #
# ######### #


@view_config(route_name='robots', request_method='GET')
def robots(request):
    """Return a robots.txt file."""
    robots_dot_txt = Robots()

    bot_delays = {
        '*': '',
        'ScoutJet': '10',
        'Baiduspider': '10',
        'BecomeBot': '20',
        'Slurp': '10'
        }

    for bot, delay in bot_delays.iteritems():
        robots_dot_txt.add_bot(bot, delay, PAGES_TO_BLOCK)

    gmt = timezone('GMT')
    # it expires in 5 days
    exp_time = datetime.now(gmt) + timedelta(5)

    resp = request.response
    resp.status = '200 OK'
    resp.content_type = 'text/plain'
    resp.cache_control = 'max-age=36000, must-revalidate'
    resp.last_modified = html_date(datetime.now(gmt))
    resp.expires = html_date(exp_time)
    resp.body = robots_dot_txt.to_string()
    return resp
