# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Export Views."""
import os
import logging
import urllib

from pyramid import httpexceptions
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from ..database import db_connect
from ..utils import (
    slugify, fromtimestamp, split_ident_hash, safe_stat,
    )
from .helpers import get_content_metadata

LEGACY_EXTENSION_MAP = {
    'epub': ['epub'],
    'pdf': ['pdf'],
    'zip': ['complete.zip', 'zip'],
}
logger = logging.getLogger('cnxarchive')


# #################### #
#   Helper functions   #
# #################### #


class ExportError(Exception):
    """Used as catchall for other export errors."""

    pass


# ######### #
#   Views   #
# ######### #


@view_config(route_name='export', request_method='GET',
             http_cache=(31536000, {'public': True}))
def get_export(request):
    """Retrieve an export file."""
    settings = get_current_registry().settings
    exports_dirs = settings['exports-directories'].split()
    args = request.matchdict
    ident_hash, type = args['ident_hash'], args['type']
    id, version = split_ident_hash(ident_hash)

    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            try:
                filename, mimetype, size, modtime, state, file_content = \
                    get_export_file(cursor, id, version, type, exports_dirs)
            except ExportError as e:
                logger.debug(str(e))
                raise httpexceptions.HTTPNotFound()

    if state == 'missing':
        raise httpexceptions.HTTPNotFound()

    encoded_filename = urllib.quote(filename.encode('utf-8'))
    resp = request.response
    resp.status = "200 OK"
    resp.content_type = mimetype
    #  Need both filename and filename* below for various browsers
    #  See: https://fastmail.blog/2011/06/24/download-non-english-filenames/
    resp.content_disposition = "attachment; filename={fname};" \
                               " filename*=UTF-8''{fname}".format(
                                       fname=encoded_filename)
    resp.body = file_content
    resp.headerlist.append(
            ('Link', '<https://{}/contents/{}/{}> ;rel="Canonical"'.format(
                            request.host, ident_hash, encoded_filename[:-4])))
    return resp


def get_export_file(cursor, id, version, type, exports_dirs):
    """Retrieve file associated with document."""
    request = get_current_request()
    type_info = dict(request.registry.settings['_type_info'])

    if type not in type_info:
        raise ExportError("invalid type '{}' requested.".format(type))

    metadata = get_content_metadata(id, version, cursor)
    file_extension = type_info[type]['file_extension']
    mimetype = type_info[type]['mimetype']
    filename = '{}@{}.{}'.format(id, version, file_extension)
    legacy_id = metadata['legacy_id']
    legacy_version = metadata['legacy_version']
    legacy_filenames = [
        '{}-{}.{}'.format(legacy_id, legacy_version, ext)
        for ext in LEGACY_EXTENSION_MAP[file_extension]
    ]
    slugify_title_filename = u'{}-{}.{}'.format(slugify(metadata['title']),
                                                version, file_extension)

    for dir in exports_dirs:
        if safe_stat(dir):
            filepath = os.path.join(dir, filename)
            try:
                with open(filepath, 'r') as file:
                    stats = os.fstat(file.fileno())
                    modtime = fromtimestamp(int(stats.st_mtime))
                    return (slugify_title_filename, mimetype,
                            stats.st_size, modtime, 'good', file.read())
            except IOError:
                # Let's see if the legacy file's there and make the new link
                legacy_filepaths = [os.path.join(dir, fn)
                                    for fn in legacy_filenames]
                for legacy_filepath in legacy_filepaths:
                    if os.path.exists(legacy_filepath):
                        with open(legacy_filepath, 'r') as file:
                            stats = os.fstat(file.fileno())
                            modtime = fromtimestamp(stats.st_mtime)
                            os.link(legacy_filepath, filepath)
                            return (slugify_title_filename, mimetype,
                                    stats.st_size, modtime, 'good',
                                    file.read())
    else:
        filenames = [filename] + legacy_filenames
        log_formatted_filenames = '\n'.join([' - {}'.format(x)
                                             for x in filenames])
        logger.error("Could not find a file for '{}' at version '{}' with "
                     "any of the following file names:\n{}"
                     .format(id, version, log_formatted_filenames))
        # No file, return "missing" state
        return (slugify_title_filename, mimetype, 0, None, 'missing', None)
