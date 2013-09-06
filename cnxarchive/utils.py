# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys
import re
import unicodedata
import uuid
from paste.deploy import appconfig


class IdentHashSyntaxError(Exception):
    """Raised when the ident-hash syntax is incorrect."""


def split_ident_hash(ident_hash):
    """Returns a valid id and version from the <id>@<version> hash syntax."""
    if '@' not in ident_hash:
        ident_hash = '{}@'.format(ident_hash)
    split_value = ident_hash.split('@')
    if split_value[0] == '':
        raise ValueError("Missing values")

    try:
        id, version = split_value
    except ValueError:
        raise IdentHashSyntaxError(ident_hash)

    # Validate the id.
    try:
        uuid.UUID(id)
    except ValueError:
        raise IdentHashSyntaxError("invalid identification value, {}" \
                                       .format(id))
    # None'ify the version on empty string.
    version = version and version or None
    return id, version


def parse_app_settings(config_uri):
    """Parse the settings from the config file for the application.
    Assumes that application section is name 'main'.
    """
    config_path = os.path.abspath(config_uri)
    return appconfig("config:{}".format(config_path), name='main')


# The import_function and template_to_regex functions are derived from
#   a WebOb documentation example.

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


MODULE_MIMETYPE = 'application/vnd.org.cnx.module'
COLLECTION_MIMETYPE = 'application/vnd.org.cnx.collection'
FOLDER_MIMETYPE = 'application/vnd.org.cnx.folder'
MIMETYPES = (MODULE_MIMETYPE, COLLECTION_MIMETYPE, FOLDER_MIMETYPE,)
PORTALTYPE_TO_MIMETYPE_MAPPING = {
    'Module': MODULE_MIMETYPE,
    'Collection': COLLECTION_MIMETYPE,
    }

def portaltype_to_mimetype(portal_type):
    """Map the given ``portal_type`` to a mimetype"""
    return PORTALTYPE_TO_MIMETYPE_MAPPING[portal_type]

def slugify(string):
    """Return a slug for the unicode_string (lowercase, only letters and
    numbers, hyphens replace spaces)
    """
    filtered_string = []
    if isinstance(string, str):
        string = unicode(string, 'utf-8')
    for i in unicodedata.normalize('NFKC', string):
        cat = unicodedata.category(i)[0]
        # filter out all the non letter and non number characters from the
        # input (L is letter and N is number)
        if cat in 'LN' or i in '-_':
            filtered_string.append(i)
        elif cat in 'Z':
            filtered_string.append(' ')
    return re.sub('\s+', '-', ''.join(filtered_string)).lower()
