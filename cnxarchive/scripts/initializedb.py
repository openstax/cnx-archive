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
from ..utils import app_settings, app_parser


def main(argv=None):
    parser = app_parser(description=__doc__)

    args = parser.parse_args(argv)

    settings = app_settings(args)
    initdb(settings)

    return 0

if __name__ == '__main__':
    main()
