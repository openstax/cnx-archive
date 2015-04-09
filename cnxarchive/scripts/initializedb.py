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

from .. import config
from ..database import initdb
from ..utils import app_settings
from ..utils import app_parser

EXAMPLE_DATA_FILEPATHS = (
    config.TEST_DATA_SQL_FILE,
    )


def main(argv=None):
    parser = app_parser(description=__doc__)

    args = parser.parse_args(argv)

    settings = app_settings(args)
    initdb(settings)

    if settings['with_example_data']:
        connection_string = settings[config.CONNECTION_STRING]
        with psycopg2.connect(connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                for filepath in EXAMPLE_DATA_FILEPATHS:
                    with open(filepath, 'r') as fb:
                        cursor.execute(fb.read())
    return 0

if __name__ == '__main__':
    main()
