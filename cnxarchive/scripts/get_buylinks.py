# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Command-line script to print the buy links given collection ids from the
plone site.
"""

import argparse
import re
import urllib2

PROPERTY_URL = 'http://cnx.org/content/{}/latest/propertyItems'

def get_buylink(url):
    content = urllib2.urlopen(url).read()
    if 'buyLink' in content:
        return re.search("'buyLink', '([^']*)'", content).group(1)
    return ''

def main():
    parser = argparse.ArgumentParser(description='Print out the buy links'
            ' of collections from the plone site')
    parser.add_argument('collection_ids', metavar='collection_id', nargs='+',
            help='Collection id, e.g. col11522')
    args = parser.parse_args()

    for collection_id in args.collection_ids:
        print collection_id, get_buylink(PROPERTY_URL.format(collection_id))
