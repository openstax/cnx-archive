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
import os
import sys
import argparse

from pyramid.paster import bootstrap

from cnxarchive.scripts._utils import create_parser
from cnxarchive.scripts.export_epub import create_epub


def main(argv=None):
    parser = create_parser('export_epub', description=__doc__)
    parser.add_argument('ident_hash',
                        help="ident-hash of the content ")
    parser.add_argument('file', type=argparse.FileType('wb'),
                        help="output file (use '-' for stdout)")
    args = parser.parse_args(argv)

    env = bootstrap(args.config_uri)

    create_epub(args.ident_hash, args.file)

    return 0
