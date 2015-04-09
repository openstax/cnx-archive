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
import datetime
import tzlocal
import argparse
from . import config
from paste.deploy import appconfig


HASH_CHAR = '@'
VERSION_CHAR = '.'


class IdentHashSyntaxError(Exception):
    """Raised when the ident-hash syntax is incorrect."""

def fromtimestamp(ts):
    return datetime.datetime.fromtimestamp(ts, tz=tzlocal.get_localzone())

def split_legacy_hash(legacy_hash):
    split_value = legacy_hash.split('/')
    id = split_value[0]
    version = None
    if len(split_value) == 2:
        if split_value[1] != 'latest':
            version = split_value[1]
    return id, version


def split_ident_hash(ident_hash, split_version=False):
    """Returns a valid id and version from the <id>@<version> hash syntax."""
    if HASH_CHAR not in ident_hash:
        ident_hash = '{}@'.format(ident_hash)
    split_value = ident_hash.split(HASH_CHAR)
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

    if split_version:
        if version is None:
            version = (None, None,)
        else:
            split_version = version.split(VERSION_CHAR)
            if len(split_version) == 1:
                split_version.append(None)
            version = tuple(split_version)
    return id, version


def join_ident_hash(id, version):
    """Returns a valid ident_hash from the given ``id`` and ``version``
    where ``id`` can be a string or UUID instance and ``version`` can be a
    string or tuple of major and minor version.
    """
    if isinstance(id, uuid.UUID):
        id = str(id)
    join_args = [id]
    if isinstance(version, (tuple, list,)):
        assert len(version) == 2, "version sequence must be two values."
        version = VERSION_CHAR.join([str(x) for x in version if x is not None])
    if version:
        join_args.append(version)
    return HASH_CHAR.join(join_args)


def app_parser(prog='cnx-archive-initdb', description=None):
    """ Command line options for the cnx-archive-initdb script
    """
    ##################################################################
    # Note: changing this function will cause the unit test          #
    # cnxarchive.tests.test_utils.ParserTestCase.test_help to fail.  #
    # To get this test to pass cnx-archive will need to be           #
    # reinstalled so the 'help' command can be updated to reflect    #
    # the new changes.                                               #
    ##################################################################
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument('config_uri', help="Configuration INI file.")
    parser.add_argument('--with-example-data', action='store_true',
                        default=False,
                        help="Initializes the database with example data.")
    parser.add_argument(
        '--user',
        action='store',
        help='Override the default user config.'
        ' A password must be given as well '
        'or else this option will be ignored')
    parser.add_argument(
        '--password',
        action='store',
        help="Suppy a password with new user")
    parser.add_argument(
        '--superuser',
        action='store',
        help='Specify a superuser.  '
        'A password must be giver '
        'as well or else this '
        'option will be ignored.')
    parser.add_argument(
        '--superpassword',
        action='store',
        help="Suppy a password for the superuser")
    parser.add_argument('--config-name',
                        action='store',
                        default='main',
                        help="Supply a name for the configuration")
    return parser


def app_settings(args):
    """Parse the settings from the config file for the application.
    The application section defaults to name 'main'.
    """
    from ast import literal_eval
    argument_dict = vars(args)

    config_path = os.path.abspath(argument_dict['config_uri'])

    # Create a settings dictionary from the congfig file.
    settings = appconfig(
        "config:{}".format(config_path), name=argument_dict['config_name'])
    connection_string = settings[config.CONNECTION_STRING]

    # create dictionary of values from the CONNECTION_STRING.
    connection_dictionary = literal_eval(
        "{\'" + connection_string.replace('=', '\':\'').replace(' ', '\', \'')
        + "\'}")
    # add the new values to the settings dictionary
    settings.update(connection_dictionary)

    # override the default user in settings.
    if argument_dict['user'] and argument_dict['password']:
        settings['user'] = argument_dict['user']
        settings['password'] = argument_dict['password']
        settings[
            config.CONNECTION_STRING] = 'dbname={dbname} ' \
                                        'user={user} ' \
                                        'password={password} ' \
                                        'host={host} ' \
                                        'port={port}'.format(**settings)
    else:
        # Make sure the user and password are None
        # since settings were not changed
        argument_dict['user'] = None
        argument_dict['password'] = None

    # Add a superuser connection string to settings
    if argument_dict['superuser'] and argument_dict['superpassword']:
        settings['superuser'] = argument_dict['superuser']
        settings['superpassword'] = argument_dict['superpassword']
        settings[
            config.SUPER_CONN_STRING] = 'dbname={dbname} ' \
                                        'user={superuser} ' \
                                        'password={superpassword} ' \
                                        'host={host} ' \
                                        'port={port}'.format(**settings)
    else:
        # make sure that superuser info is None
        # since super-connection-string was not
        # generated.
        settings[config.SUPER_CONN_STRING] = None
        argument_dict['superuser'] = None
        argument_dict['superpassword'] = None

    # Remove keys from argument_dict if their values are None
    argument_dict = {k: v for k, v in argument_dict.items() if v is not None}

    # Add any remaining arguments to the settings dictionary.
    settings.update(argument_dict)

    return settings


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

def escape(s):
    """xml/html entity escaping of < > and &"""
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', "&quot;")
    return s


def utf8(item):
    """Change all python2 str/bytes instances to unicode/python3 str
    """
    if isinstance(item, list):
        return [utf8(i) for i in item]
    if isinstance(item, tuple):
        return tuple([utf8(i) for i in item])
    if isinstance(item, dict):
        return {utf8(k): utf8(v) for k, v in item.items()}
    try:
        return item.decode('utf-8')
    except: # bare except since this method is supposed to be safe anywhere
        return item
