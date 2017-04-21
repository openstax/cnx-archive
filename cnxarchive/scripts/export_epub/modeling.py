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
    get_type,
    )


def document_factory(ident_hash, context=None, baked=False):
    metadata = get_metadata(ident_hash)
    if baked and context is None:
        raise RuntimeError("Request for baked Document with no context")

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
        if hash == 'resources':
            # if ref.uri is just /resources/hash (without filename)
            hash = filename
        try:
            resource = resources_map[hash]
        except KeyError:  # reference w/o resource
            resource = resource_factory(hash)

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


def tree_to_nodes(tree, context=None, metadata=None):
    """Assembles ``tree`` nodes into object models.
    If ``context`` is supplied, it will be used to contextualize
    the contents of the nodes. Metadata will pass non-node identifying
    values down to child nodes, if not overridden (license, timestamps, etc)
    """
    nodes = []
    for item in tree['contents']:
        if 'contents' in item:
            sub_nodes = tree_to_nodes(item, context=context, metadata=metadata)
            if metadata is None:
                metadata = {}
            else:
                metadata = metadata.copy()
                for key in ('title', 'id', 'shortid',
                            'cnx-archive-uri', 'cnx-archive-shortid'):
                    if key in metadata:
                        metadata.pop(key)

            for key in ('title', 'id', 'shortId'):
                if item.get(key):
                    metadata[key] = item[key]
                    if item[key] != 'subcol':
                        if key == 'id':
                            metadata['cnx-archive-uri'] = item[key]
                        elif key == 'shortId':
                            metadata['cnx-archive-shortid'] = item[key]

            titles = _title_overrides_from_tree(item)
            if item.get('id') is not None:
                tbinder = cnxepub.Binder(item.get('id'),
                                         sub_nodes,
                                         metadata=metadata,
                                         title_overrides=titles)
            else:
                tbinder = cnxepub.TranslucentBinder(sub_nodes,
                                                    metadata=metadata,
                                                    title_overrides=titles)
            nodes.append(tbinder)
        else:
            doc = document_factory(item['id'], context=context)
            for key in ('title', 'id', 'shortId'):
                if item.get(key):
                    doc.metadata[key] = item[key]
                    if key == 'id':
                        doc.metadata['cnx-archive-uri'] = item[key]
                    elif key == 'shortId':
                        doc.metadata['cnx-archive-shortid'] = item[key]
            nodes.append(doc)
    return nodes


def binder_factory(ident_hash, baked=False):
    metadata = get_metadata(ident_hash)
    tree = get_tree(ident_hash, baked=baked)
    if baked:
        context = tree['id']
    else:
        context = None
    nodes = tree_to_nodes(tree, context, metadata)
    titles = _title_overrides_from_tree(tree)
    resources = [resource_factory(h, ident_hash)
                 for h in get_registered_files(ident_hash)]
    binder = cnxepub.Binder(metadata['id'], nodes=nodes, metadata=metadata,
                            resources=resources, title_overrides=titles)
    return binder


def _type_to_factory(type):
    try:
        factory = {'Module': document_factory,
                   'Collection': binder_factory,
                   'SubCollection': binder_factory,
                   }[type]
    except KeyError:  # pragma: no cover
        raise RuntimeError("unknown type: {}".format(type))
    return factory


def factory(ident_hash, baked=False):
    factory_callable = _type_to_factory(get_type(ident_hash))
    return factory_callable(ident_hash, baked=baked)


def create_epub(ident_hash, file, format='raw'):
    """Creates an epub from an ``ident_hash``, which is output to the given
    ``file`` (a file-like object).
    Returns None, writes to the given ``file``.

    """
    model = factory(ident_hash, baked=(format != 'raw'))
    if isinstance(model, cnxepub.Document):
        model = cnxepub.TranslucentBinder(nodes=[model])
    cnxepub.make_epub(model, file)


__all__ = (
    'create_epub',
    'binder_factory',
    'document_factory',
    'factory',
    'resource_factory',
    'tree_to_nodes',
    )
