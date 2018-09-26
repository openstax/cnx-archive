# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Legacy Redirect Views."""
import logging

from cnxepub.models import flatten_tree_to_ident_hashes
from pyramid import httpexceptions
from pyramid.threadlocal import get_current_registry
from pyramid.view import view_config

from .. import config
from ..database import SQL, db_connect
from ..utils import (
    join_ident_hash, split_legacy_hash
    )
from .content import _get_content_json

logger = logging.getLogger('cnxarchive')

# #################### #
#   Helper functions   #
# #################### #


def _get_page_in_book(page_uuid, page_version, book_uuid,
                      book_version, latest=False):
    book_ident_hash = join_ident_hash(book_uuid, book_version)
    coltree = _get_content_json(ident_hash=book_ident_hash)['tree']
    if coltree is None:
        raise httpexceptions.HTTPNotFound()
    pages = list(flatten_tree_to_ident_hashes(coltree))
    page_ident_hash = join_ident_hash(page_uuid, page_version)
    if page_ident_hash in pages:
        return book_uuid, '{}:{}'.format(
            latest and book_uuid or book_ident_hash, page_uuid)
    # book not in page
    return page_uuid, page_ident_hash


def _convert_legacy_id(objid, objver=None):
    with db_connect() as db_connection:
        with db_connection.cursor() as cursor:
            if objver:
                args = dict(objid=objid, objver=objver)
                cursor.execute(SQL['get-content-from-legacy-id-ver'], args)
            else:
                cursor.execute(SQL['get-content-from-legacy-id'],
                               dict(objid=objid))
            try:
                id, version = cursor.fetchone()
                return (id, version)
            except TypeError:  # None returned
                return (None, None)


# ######### #
#   Views   #
# ######### #


@view_config(route_name='legacy-redirect', request_method='GET',
             http_cache=(60, {'public': True}))
@view_config(route_name='legacy-redirect-latest', request_method='GET',
             http_cache=(60, {'public': True}))
@view_config(route_name='legacy-redirect-w-version', request_method='GET',
             http_cache=(60, {'public': True}))
def redirect_legacy_content(request):
    """Redirect from legacy /content/id/version to new /contents/uuid@version.

    Handles collection context (book) as well.
    """
    routing_args = request.matchdict
    objid = routing_args['objid']
    objver = routing_args.get('objver')
    filename = routing_args.get('filename')

    id, version = _convert_legacy_id(objid, objver)

    if not id:
        raise httpexceptions.HTTPNotFound()

    # We always use 301 redirects (HTTPMovedPermanently) here
    # because we want search engines to move to the newer links
    # We cache these redirects only briefly because, even when versioned,
    # legacy collection versions don't include the minor version,
    # so the latest archive url could change
    if filename:
        with db_connect() as db_connection:
            with db_connection.cursor() as cursor:
                args = dict(id=id, version=version, filename=filename)
                cursor.execute(SQL['get-resourceid-by-filename'], args)
                try:
                    res = cursor.fetchone()
                    resourceid = res[0]

                    raise httpexceptions.HTTPMovedPermanently(
                         request.route_path('resource', hash=resourceid,
                                            ignore=u'/{}'.format(filename)),
                         headers=[("Cache-Control", "max-age=60, public")])
                except TypeError:  # None returned
                    raise httpexceptions.HTTPNotFound()

    ident_hash = join_ident_hash(id, version)
    params = request.params
    if params.get('collection'):  # page in book
        objid, objver = split_legacy_hash(params['collection'])
        book_uuid, book_version = _convert_legacy_id(objid, objver)
        if book_uuid:
            id, ident_hash = \
                _get_page_in_book(id, version, book_uuid, book_version)

    raise httpexceptions.HTTPMovedPermanently(
        request.route_path('content', ident_hash=ident_hash),
        headers=[("Cache-Control", "max-age=60, public")])
