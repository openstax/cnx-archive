# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Command-line script to take collection ids as arguments, get the buy link
for each collection from the plone site and insert into the database.
"""

import argparse
import re
import urllib2
import sys

import psycopg2

from ..database import CONNECTION_SETTINGS_KEY, SQL
from ..utils import parse_app_settings

PROPERTY_URL = 'http://cnx.org/content/{}/latest/propertyItems'

def get_buylink(url):
    content = urllib2.urlopen(url).read()
    if 'buyLink' in content:
        return re.search("'buyLink', '([^']*)'", content).group(1)

def main():
    parser = argparse.ArgumentParser(description='Insert the buy links'
            ' of collections from the plone site into the database')
    parser.add_argument('config_uri', help='Config URI, e.g. development.ini')
    parser.add_argument('collection_ids', metavar='collection_id', nargs='+',
            help='Collection id, e.g. col11522')
    args = parser.parse_args()

    try:
        settings = parse_app_settings(args.config_uri)
    except:
        parser.print_help()
        sys.exit(1)

    with psycopg2.connect(settings[CONNECTION_SETTINGS_KEY]) as db_connection:
        with db_connection.cursor() as cursor:
            for collection_id in args.collection_ids:
                buylink = get_buylink(PROPERTY_URL.format(collection_id))
                if not buylink:
                    continue
                query = SQL['update-buylink']
                args = {'moduleid': collection_id, 'buylink': buylink}
                cursor.execute(query, args)
