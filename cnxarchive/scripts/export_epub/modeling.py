# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Logic used to initialize models from the archive database.

"""
import io
from contextlib import contextmanager

import cnxepub

from cnxarchive.scripts.export_epub.db import (
    get_content,
    get_file,
    get_file_info,
    get_metadata,
    get_registered_files,
    )


def document_factory(ident_hash, context=None):
    metadata = get_metadata(ident_hash)
    content = get_content(ident_hash, context)
    resources_map = {h: resource_factory(h, ident_hash)
                     for h in get_registered_files(ident_hash)}
    doc = cnxepub.Document(ident_hash, content, metadata=metadata,
                           resources=resources_map.values())
    # FIXME the referencing binding template doesn't allow for more than
    # the `id` to be set. Change this to allow an anonymous function.
    for ref in doc.references:
        if ref.remote_type != 'internal' \
           or not ref.uri.startswith('/resources/'):
            continue
        hash, filename = ref.uri.split('/')[-2:]
        resource = resources_map[hash]
        ref.bind(resource, '/resources/{}')
    return doc


class ArchiveResource(cnxepub.Resource):

    def __init__(self, hash, context=None):
        self.id = hash
        self._hash = hash
        self.filename, self.media_type = get_file_info(hash, context)

    @contextmanager
    def open(self):
        yield io.BytesIO(get_file(self.hash))


resource_factory = ArchiveResource


__all__ = (
    'document_factory',
    'resource_factory',
    )
