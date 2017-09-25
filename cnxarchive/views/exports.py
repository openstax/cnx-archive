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

from pyramid import httpexceptions
from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.view import view_config

from .. import config
from ..database import db_connect
from ..utils import (
    slugify, fromtimestamp, split_ident_hash,
    )
from .helpers import get_content_metadata

LEGACY_EXTENSION_MAP = {'epub': 'epub', 'pdf': 'pdf', 'zip': 'complete.zip'}
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


@view_config(route_name='export', request_method='GET')
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

    resp = request.response
    resp.status = "200 OK"
    resp.content_type = mimetype
    resp.content_disposition = u'attached; filename={}'.format(filename)
    resp.body = file_content
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
    legacy_filename = '{}-{}.{}'.format(
        legacy_id, legacy_version, LEGACY_EXTENSION_MAP[file_extension])
    slugify_title_filename = u'{}-{}.{}'.format(slugify(metadata['title']),
                                                version, file_extension)

    for exports_dir in exports_dirs:
        filepath = os.path.join(exports_dir, filename)
        legacy_filepath = os.path.join(exports_dir, legacy_filename)
        try:
            with open(filepath, 'r') as file:
                stats = os.fstat(file.fileno())
                modtime = fromtimestamp(int(stats.st_mtime))
                return (slugify_title_filename, mimetype,
                        stats.st_size, modtime, 'good', file.read())
        except IOError:
            # Let's see if the legacy file's there and make the new link if so
            # FIXME remove this code when we retire legacy
            try:
                with open(legacy_filepath, 'r') as file:
                    stats = os.fstat(file.fileno())
                    modtime = fromtimestamp(stats.st_mtime)
                    os.link(legacy_filepath, filepath)
                    return (slugify_title_filename, mimetype,
                            stats.st_size, modtime, 'good', file.read())
            except IOError as e:
                # to be handled by the else part below if unable to find file
                # in any of the export dirs
                if not str(e).startswith('[Errno 2] No such file or direct'):
                    logger.warn('IOError when accessing legacy export file:\n'
                                'exception: {}\n'
                                'filepath: {}\n'
                                .format(str(e), legacy_filepath))
    else:
        # No file, return "missing" state
        return (slugify_title_filename, mimetype, 0, None, 'missing', None)
