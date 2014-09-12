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
import argparse
import gzip

import psycopg2
from .. import config
from ..utils import parse_app_settings, split_ident_hash


LOG_FORMAT_PLAIN = 'plain'
LOG_FORMAT_GZ = 'gz'
LOG_FORMATS = [LOG_FORMAT_PLAIN, LOG_FORMAT_GZ]
_log_openers = [open, gzip.open]
LOG_FORMAT_OPENERS_MAPPING = dict(zip(LOG_FORMATS, _log_openers))

URL_PATTERN_TMPLT = "^http://{}/contents/([-a-f0-9]+)@([.0-9]+)$"


SQL_GET_MODULE_IDENT_BY_UUID_N_VERSION = """\
SELECT module_ident FROM modules
  WHERE uuid = %s::uuid
        AND concat_ws('.', major_version, minor_version) = %s
;
"""

def parse_log(log, url_pattern):
    """Given a buffer as ``log``, parse the log bufer into
    a mapping of ident-hashes to a hit count,
    the timestamp of the initial log,
    and the last timestamp in the log.
    """
    hits = {}
    initial_timestamp = None
    clean_timestamp = lambda v: ' '.join(v).strip('[]')
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hostname', default='cnx.org',
                        help="hostname of the site (default: cnx.org)")
    parser.add_argument('--log-format',
                        default=LOG_FORMAT_GZ, choices=LOG_FORMATS,
                        help="(default: {})".format(LOG_FORMAT_GZ))
    parser.add_argument('--config-name', default='main',
                        help="section name for the application in the " \
                             "configuration file (default: main)")
    parser.add_argument('config_uri', help="Configuration INI file.")
    parser.add_argument('log_file',
                        help="path to the logfile.")
    args = parser.parse_args(argv)

    opener = LOG_FORMAT_OPENERS_MAPPING[args.log_format]

    # Build the URL pattern.
    hostname = args.hostname.replace('.', '\.')
    url_pattern = URL_PATTERN_TMPLT.format(args.hostname)
    url_pattern = re.compile(url_pattern)

    # Parse the log to structured data.
    with opener(args.log_file) as log:
        hits, start_timestamp, end_timestamp = parse_log(log, url_pattern)

    # Parse the configuration file for the postgres connection string.
    settings = parse_app_settings(args.config_uri,  args.config_name)

    # Insert the hits into the database.
    connection_string = settings[config.CONNECTION_STRING]
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            for ident_hash, hit_count in hits.items():
                cursor.execute(SQL_GET_MODULE_IDENT_BY_UUID_N_VERSION,
                               split_ident_hash(ident_hash))
                module_ident = cursor.fetchone()
                payload = (module_ident, start_timestamp, end_timestamp,
                           hit_count,)
                cursor.execute("INSERT INTO document_hits "
                               "  VALUES (%s, %s, %s, %s);",
                               payload)
            cursor.execute("SELECT update_hit_ranks();")
    return 0


if __name__ == '__main__':
    main()
