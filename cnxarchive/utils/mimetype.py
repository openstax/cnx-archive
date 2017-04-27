# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Methods for handling mimetypes."""

__all__ = (
    'COLLECTION_MIMETYPE',
    'SUBCOLLECTION_MIMETYPE',
    'FOLDER_MIMETYPE',
    'MIMETYPES',
    'MODULE_MIMETYPE',
    'COMPOSITE_MODULE_MIMETYPE',
    'PORTALTYPE_TO_MIMETYPE_MAPPING',
    'portaltype_to_mimetype',
    )


MODULE_MIMETYPE = 'application/vnd.org.cnx.module'
COMPOSITE_MODULE_MIMETYPE = 'application/vnd.org.cnx.composite-module'
COLLECTION_MIMETYPE = 'application/vnd.org.cnx.collection'
SUBCOLLECTION_MIMETYPE = 'application/vnd.org.cnx.subcollection'
FOLDER_MIMETYPE = 'application/vnd.org.cnx.folder'
MIMETYPES = (MODULE_MIMETYPE, COLLECTION_MIMETYPE, FOLDER_MIMETYPE,)
PORTALTYPE_TO_MIMETYPE_MAPPING = {
    'Module': MODULE_MIMETYPE,
    'CompositeModule': COMPOSITE_MODULE_MIMETYPE,
    'Collection': COLLECTION_MIMETYPE,
    'SubCollection': SUBCOLLECTION_MIMETYPE,
    }


def portaltype_to_mimetype(portal_type):
    """Map the given ``portal_type`` to a mimetype."""
    return PORTALTYPE_TO_MIMETYPE_MAPPING[portal_type]
