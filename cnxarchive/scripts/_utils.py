# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Utility methods for commandline scripts."""

import os
import argparse

from pyramid.paster import get_appsettings


__all__ = ('create_parser', 'get_app_settings_from_arguments',)


BASE_PROG_NAME = 'cnx-archive'
PROG_PATTERN = '{base_name}-{sub_name}'


def _gen_prog_name(sub_name, base_name=BASE_PROG_NAME):
    return PROG_PATTERN.format(base_name=BASE_PROG_NAME,
                               sub_name=sub_name)


def create_parser(name, description=None):
    """Create an argument parser with the given ``name`` and ``description``.

    The name is used to make ``cnx-archive-<name>`` program name.
    This creates and returns a parser with
    the ``config_uri`` argument declared.
    """
    prog = _gen_prog_name(name)
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument('config_uri', help="Configuration INI file.")
    parser.add_argument('--config-name',
                        action='store',
                        default='main',
                        help="Supply a section name in the configuration")
    return parser


def get_app_settings_from_arguments(args):
    """Parse ``argparse`` style arguments into app settings.

    Given an ``argparse`` set of arguments as ``args``
    parse the arguments to return the application settings.
    This assumes the parser was created using ``create_parser``.
    """
    config_filepath = os.path.abspath(args.config_uri)
    return get_appsettings(config_filepath, name=args.config_name)
