# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Commandline script used to capture document hit statistics.

This parses a Varnish-Cache log file for document access lines.
Each line is processed as a hit for a document.
The counts are processed into a time range
and inserted into the cnx-archive database.
"""
import re
import gzip

import psycopg2
from cnxarchive import config
from cnxarchive.scripts._utils import (
    create_parser, get_app_settings_from_arguments,
    )


LOG_FORMAT_PLAIN = 'plain'
LOG_FORMAT_GZ = 'gz'
LOG_FORMATS = [LOG_FORMAT_PLAIN, LOG_FORMAT_GZ]
_log_openers = [open, gzip.open]
LOG_FORMAT_OPENERS_MAPPING = dict(zip(LOG_FORMATS, _log_openers))

URL_PATTERN_TMPLT = "^http://{}/contents/([-a-f0-9]+)@([.0-9]+)$"


def parse_log(log, url_pattern):
    """Parse ``log`` buffer based on ``url_pattern``.

    Given a buffer as ``log``, parse the log buffer into
    a mapping of ident-hashes to a hit count,
    the timestamp of the initial log,
    and the last timestamp in the log.
    """
    hits = {}
    initial_timestamp = None

    def clean_timestamp(v):
        return ' '.join(v).strip('[]')
    for line in log:
        data = line.split()
        if not initial_timestamp:
            initial_timestamp = clean_timestamp(data[3:5])
        match = url_pattern.match(data[6])
        if match:
            ident_hash = '@'.join(match.groups())
            if ident_hash:
                hits[ident_hash] = hits.get(ident_hash, 0) + 1
    else:
        end_timestamp = clean_timestamp(data[3:5])
    return hits, initial_timestamp, end_timestamp


def main(argv=None):
    """Count the hits from logfile."""
    parser = create_parser('hits_counter', description=__doc__)
    parser.add_argument('--hostname', default='cnx.org',
                        help="hostname of the site (default: cnx.org)")
    parser.add_argument('--log-format',
                        default=LOG_FORMAT_GZ, choices=LOG_FORMATS,
                        help="(default: {})".format(LOG_FORMAT_GZ))
    parser.add_argument('log_file',
                        help="path to the logfile.")
    args = parser.parse_args(argv)

    opener = LOG_FORMAT_OPENERS_MAPPING[args.log_format]

    # Build the URL pattern.
    hostname = args.hostname.replace('.', '\.')
    url_pattern = URL_PATTERN_TMPLT.format(hostname)
    url_pattern = re.compile(url_pattern)

    # Parse the log to structured data.
    with opener(args.log_file) as log:
        hits, start_timestamp, end_timestamp = parse_log(log, url_pattern)

    # Parse the configuration file for the postgres connection string.
    settings = get_app_settings_from_arguments(args)

    # Insert the hits into the database.
    connection_string = settings[config.CONNECTION_STRING]
    db_connection = psycopg2.connect(connection_string)
    with db_connection:
        with db_connection.cursor() as cursor:
            for ident_hash, hit_count in hits.items():
                cursor.execute("""\
                      INSERT INTO document_hits
                        (documentid, start_timestamp, end_timestamp, hits)
                      SELECT module_ident, %s, %s, %s
                      FROM modules WHERE
                        ident_hash(uuid, major_version, minor_version) = %s""",
                               (start_timestamp, end_timestamp, hit_count,
                                ident_hash))
            cursor.execute("SELECT update_hit_ranks();")
    db_connection.close()
    return 0


if __name__ == '__main__':
    main()
