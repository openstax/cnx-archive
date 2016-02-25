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
    get_tree,
    )


def document_factory(ident_hash, context=None):
    metadata = get_metadata(ident_hash)
    content = get_content(ident_hash, context)
    resources_map = {h: resource_factory(h, ident_hash)
                     for h in get_registered_files(ident_hash)}
    doc = cnxepub.Document(metadata['id'], content, metadata=metadata,
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


def _title_overrides_from_tree(tree):
    """Returns the title overrides for the top layer of the tree."""
    return [x.get('title', None) for x in tree['contents']]


def tree_to_nodes(tree, context=None):
    """Assembles ``tree`` nodes into object models.
    If ``context`` is supplied, it will be used to contextualize
    the contents of the nodes.

    """
    nodes = []
    for item in tree['contents']:
        if 'contents' in item:
            sub_nodes = tree_to_nodes(item, context=context)
            titles = _title_overrides_from_tree(item)
            tbinder = cnxepub.TranslucentBinder(sub_nodes,
                                                title_overrides=titles)
            nodes.append(tbinder)
        else:
            nodes.append(document_factory(item['id'], context=context))
    return nodes


def binder_factory(ident_hash):
    metadata = get_metadata(ident_hash)
    tree = get_tree(ident_hash)
    nodes = tree_to_nodes(tree)
    titles = _title_overrides_from_tree(tree)
    resources = [resource_factory(h, ident_hash)
                 for h in get_registered_files(ident_hash)]
    binder = cnxepub.Binder(metadata['id'], nodes=nodes, metadata=metadata,
                            resources=resources, title_overrides=titles)
    return binder


__all__ = (
    'binder_factory',
    'document_factory',
    'resource_factory',
    'tree_to_nodes',
    )
