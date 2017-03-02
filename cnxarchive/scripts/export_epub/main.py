# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Commandline script used to create an internal EPUB for content.

"""
from __future__ import print_function
import sys
import argparse

from pyramid.paster import bootstrap

from cnxarchive.scripts._utils import create_parser
from cnxarchive.scripts.export_epub import create_epub


def main(argv=None):
    parser = create_parser('export_epub', description=__doc__)
    parser.add_argument('-f', '--format', default='raw',
                        help="epub format: raw, baked, hybrid; default raw ")
    parser.add_argument('ident_hash',
                        help="ident-hash of the content ")
    parser.add_argument('file', type=argparse.FileType('wb'),
                        help="output file")
    args = parser.parse_args(argv)

    if args.file is sys.stdout:
        raise RuntimeError("Can't stream a zipfile to stdout "
                           "because it will have issues closing")
    env = bootstrap(args.config_uri)

    create_epub(args.ident_hash, args.file, args.format)

    return 0
