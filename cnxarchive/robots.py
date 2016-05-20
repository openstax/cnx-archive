# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Classes for generating robots.txt page in a configurable way."""


from pyramid.threadlocal import get_current_registry


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
