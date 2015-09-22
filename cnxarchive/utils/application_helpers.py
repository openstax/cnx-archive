# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""The import_function and template_to_regex functions are derived from
a WebOb documentation example.
"""
import os
import sys
import re

from paste.deploy import appconfig


__all__ = ('import_function', 'get_appsettings', 'template_to_regex',)


# FFF (11-Sept-2015) from pyramid.paster import get_appsettings
#     Please remove this in favor of importing pyramid's version
#     in all locations where this function is used.
def get_appsettings(config_uri, name='main', options=None,
                    appconfig=appconfig):
    """Parse the settings from the config file for the application.
    The application section defaults to name 'main'.
    """
    config_filepath = os.path.abspath(config_uri)
    settings = appconfig("config:{}".format(config_filepath),
                         name=name)
    return settings


def import_function(import_line):
    """imports a controller function using the ``<module-path>:<function>``
    syntax."""
    module_name, func_name = import_line.split(':', 1)
    __import__(module_name)
    module = sys.modules[module_name]
    func = getattr(module, func_name)
    return func


var_regex = re.compile(r'''
    \{          # The exact character "{"
    (\w+)       # The variable name (restricted to a-z, 0-9, _)
    (?::([^}]+))? # The optional :regex part
    \}          # The exact character "}"
    ''', re.VERBOSE)
def template_to_regex(template):
    regex = ''
    last_pos = 0
    for match in var_regex.finditer(template):
        regex += re.escape(template[last_pos:match.start()])
        var_name = match.group(1)
        expr = match.group(2) or '[^/]+'
        expr = '(?P<%s>%s)' % (var_name, expr)
        regex += expr
        last_pos = match.end()
    regex += re.escape(template[last_pos:])
    regex = '^%s$' % regex
    return regex
