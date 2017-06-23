# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Views and Classes for robots.txt page."""
from datetime import datetime, timedelta

from pytz import timezone
from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

PAGES_TO_BLOCK = [
    'legacy.cnx.org', '/lenses', '/browse_content', '/content/', '/content$',
    '/*/pdf$', '/*/epub$', '/*/complete$',
    '/*/offline$', '/*?format=*$', '/*/multimedia$', '/*/lens_add?*$',
    '/lens_add', '/*/lens_view/*$', '/content/*view_mode=statistics$']


# #################### #
#   Helper functions   #
# #################### #


class Robots(object):
    """Singleton class for a robots.txt response."""

    def __init__(self, sitemap=None, bots=None):
        """Initialize a robots.txt, with path to sitemap."""

        if sitemap is None:
            sitemap = str(
                get_current_registry().settings['sitemap-destination'])

        self.sitemap = sitemap
        self.bots = bots or []

    def add_bot(self, bot_name, delay, pages_to_block):
        """Add a bot to the robots.txt."""
        self.bots.append(Bot(bot_name, delay, pages_to_block))

    def __str__(self):
        """String version of robots.txt."""
        ret_str = 'Sitemap: ' + self.sitemap + '\n'
        for bot in self.bots:
            ret_str += bot.to_string() + '\n'
        return ret_str

    def to_string(self):
        """Return string."""
        return self.__str__()


class Bot(object):
    """Details of individual bots needed for generating robots.txt."""

    def __init__(self, bot_name, delay, pages_to_block):
        """Initialize bot."""
        self.name = bot_name
        self.delay = delay
        self.blocked = pages_to_block

    def __str__(self):
        """Return string blocking settings for this bot for robots.txt."""
        ret_str = 'User-agent: ' + self.name + '\n'
        if self.delay:
            ret_str += 'Crawl-delay: ' + self.delay + '\n'
        for page in self.blocked:
            ret_str += 'Disallow: ' + page + '\n'
        return ret_str

    def to_string(self):
        """Return string."""
        return self.__str__()


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
