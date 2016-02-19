# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Commandline script used to initialize the SQL database."""
from __future__ import print_function
import sys

import psycopg2

from cnxarchive import config
from cnxarchive.database import initdb
from cnxarchive.scripts._utils import (
    create_parser, get_app_settings_from_arguments,
    )


EXAMPLE_DATA_FILEPATHS = (
    config.TEST_DATA_SQL_FILE,
    )


def main(argv=None):
    """Initialize the database."""
    parser = create_parser('initdb', description=__doc__)
    parser.add_argument('--with-example-data', action='store_true',
                        help="Initializes the database with example data.")
    parser.add_argument('--superuser', action='store',
                        help="NOT IMPLEMENTED")
    parser.add_argument('--super-password', action='store',
                        help="NOT IMPLEMENTED")
    args = parser.parse_args(argv)

    settings = get_app_settings_from_arguments(args)
    try:
        initdb(settings)
    except psycopg2.InternalError as exc:
        print("Error:  {}".format(exc.args[0]), file=sys.stderr)
        return 1

    if args.with_example_data:
        connection_string = settings[config.CONNECTION_STRING]
        with psycopg2.connect(connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                for filepath in EXAMPLE_DATA_FILEPATHS:
                    with open(filepath, 'r') as fb:
                        cursor.execute(fb.read())
    return 0


if __name__ == '__main__':
    main()
