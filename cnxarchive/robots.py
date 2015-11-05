# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals

from . import IS_PY2


class Robots(object):
    def __init__(self, sitemap='http://cnx.org/sitemap.xml', bots=None):
        self.sitemap = sitemap
        self.bots = bots or []

    def add_bot(self, bot_name, delay, pages_to_block):
        self.bots.append(Bot(bot_name, delay, pages_to_block))

    def to_string(self):
        ret_str = 'Sitemap: ' + self.sitemap + '\n'
        for bot in self.bots:
            ret_str += bot.to_string() + '\n'
        return ret_str

    def __str__(self):
        if IS_PY2:
            return self.to_string().encode('utf-8')
        return self.to_string()

    def __unicode__(self):
        # FIXME remove when we no longer need to support python 2
        return self.to_string()

    def __bytes__(self):
        return self.to_string().encode('utf-8')


class Bot(object):
    def __init__(self, bot_name, delay, pages_to_block):
        self.name = bot_name
        self.delay = delay
        self.blocked = pages_to_block

    def to_string(self):
        ret_str = 'User-agent: ' + self.name + '\n'
        if self.delay:
            ret_str += 'Crawl-delay: ' + self.delay + '\n'
        for page in self.blocked:
            ret_str += 'Disallow: ' + page + '\n'
        return ret_str

    def __str__(self):
        if IS_PY2:
            return self.to_string().encode('utf-8')
        return self.to_string()

    def __unicode__(self):
        # FIXME remove when we no longer need to support python 2
        return self.to_string()

    def __bytes__(self):
        return self.to_string().encode('utf-8')
