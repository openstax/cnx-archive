# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Memcached utilities."""

import binascii
import copy
import hashlib

import memcache
from pyramid.threadlocal import get_current_registry

from .search import search as database_search


def search(query, query_type, nocache=False):
    """Search archive contents.

    Look up search results in cache, if not in cache,
    do a database search and cache the result
    """
    settings = get_current_registry().settings
    memcache_servers = settings['memcache-servers'].split()
    if not memcache_servers:
        # memcache is not enabled, do a database search directly
        return database_search(query, query_type)

    # sort query params and create a key for the search
    search_params = []
    search_params += copy.deepcopy(query.terms)
    search_params += copy.deepcopy(query.filters)
    search_params += [('sort', i) for i in query.sorts]
    search_params.sort(key=lambda record: (record[0], record[1]))
    search_params.append(('query_type', query_type))

    # search_key should look something like:
    # '"sort:pubDate" "text:college physics" "query_type:weakAND"'
    search_key = u' '.join([u'"{}"'.format(u':'.join(param))
                           for param in search_params])
    # hash the search_key so it never exceeds the key length limit (250) in
    # memcache
    mc_search_key = binascii.hexlify(
        hashlib.pbkdf2_hmac('sha1', search_key.encode('utf-8'), b'', 1))

    # look for search results in memcache first, unless nocache
    mc = memcache.Client(memcache_servers,
                         server_max_value_length=128*1024*1024, debug=0)

    if not nocache:
        search_results = mc.get(mc_search_key)
    else:
        search_results = None

    if not search_results:
        # search results is not in memcache, do a database search
        search_results = database_search(query, query_type)

        cache_length = int(settings['search-cache-expiration'])

        # for particular searches, store in memcache for longer
        if (len(search_params) == 2 and
                # search by subject
                search_params[0][0] == 'subject' or
                # search single terms
                search_params[0][0] == 'text' and
                                       ' ' not in search_params[0][1]):
                # search with one term or one filter, plus query_type
            cache_length = int(settings['search-long-cache-expiration'])

        # store in memcache
        mc.set(mc_search_key, search_results, time=cache_length,
               min_compress_len=1024*1024)  # compress when > 1MB

    # return search results
    return search_results
