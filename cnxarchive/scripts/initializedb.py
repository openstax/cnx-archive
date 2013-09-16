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
import argparse

import psycopg2
from ..database import initdb
from ..utils import parse_app_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config_uri', help="Configuration INI file.")

    args = parser.parse_args(argv)
    settings = parse_app_settings(args.config_uri)
    initdb(settings)
    return 0

if __name__ == '__main__':
    main()
