# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Commandline script used to initialize the SQL database."""
import os
import sys

import psycopg2
from ..database import initdb
from ..utils import parse_app_settings


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    try:
        settings = parse_app_settings(config_uri)
    except:
        usage(argv)
    initdb(settings)
