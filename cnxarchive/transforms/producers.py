# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Producer functions that wrap basic transforms to create complete docs."""
import hashlib
from io import BytesIO

from lxml import etree

from .converters import (
    DEFAULT_XMLPARSER,
    cnxml_to_html, cnxml_to_full_html,
    html_to_cnxml, html_to_full_cnxml,
    )
from .resolvers import resolve_cnxml_urls, resolve_html_urls


__all__ = (
    'MissingDocumentOrSource', 'MissingAbstract', 'IndexFileExistsError',
    'produce_cnxml_for_abstract', 'produce_html_for_abstract',
    'produce_cnxml_for_module', 'produce_html_for_module',
    'transform_abstract_to_cnxml', 'transform_abstract_to_html',
    'transform_module_content',
    )


TRANSFORM_TYPES = {
    'cnxml2html': (cnxml_to_full_html, resolve_cnxml_urls, 'text/html',),
    'html2cnxml': (html_to_full_cnxml, resolve_html_urls, 'text/xml',),
    }


class MissingDocumentOrSource(Exception):
    """Document or source XML document cannot be found."""

    def __init__(self, document_ident, filename):
        """Create exception with details."""
        self.document_ident = document_ident
        self.filename = filename
        msg = "Cannot find document (at ident: {}) " \
              "or file with filename '{}'." \
              .format(self.document_ident, self.filename)
        super(MissingDocumentOrSource, self).__init__(msg)


class MissingAbstract(Exception):
    """Used to signify that the abstract is missing from a document entry."""

    def __init__(self, document_ident):
        """Create exception with details."""
        self.document_ident = document_ident
        msg = "Cannot find abstract for document (at ident: {})." \
            .format(self.document_ident)
        super(MissingAbstract, self).__init__(msg)


class IndexFileExistsError(Exception):
    """Raised when index.** file for an ident already exists.

    Not raised if we are overwriting it.
    """

    def __init__(self, document_ident, filename):
        """Create exception with details."""
        message = 'One of {} already exists for document {}' \
            .format(filename, document_ident)
        super(IndexFileExistsError, self).__init__(message)


def produce_html_for_abstract(plpy, document_ident):
    """Produce html for the abstract by the given ``document_ident``."""
    plan = plpy.prepare("SELECT abstractid, abstract "
                        "FROM modules NATURAL LEFT JOIN abstracts "
                        "WHERE module_ident = $1;", ('integer',))
    try:
        result = plpy.execute(plan, (document_ident,), 1)[0]
        abstractid, abstract = result['abstractid'], result['abstract']
    except (IndexError, KeyError):
        # This means the document doesn't exist.
        raise ValueError("No document at ident: {}".format(document_ident))
    if abstractid is None:
        raise MissingAbstract(document_ident)

    warning_messages = None
    # Transform the abstract.
    if abstract:
        html, warning_messages = transform_abstract_to_html(
            abstract, document_ident, plpy)
    else:
        html = None

    # Update the abstract.
    if html:
        plan = plpy.prepare("UPDATE abstracts SET (html) = ($1) "
                            "WHERE abstractid = $2;", ('text', 'integer'))
        plpy.execute(plan, (html, abstractid,))
    return warning_messages


def produce_cnxml_for_abstract(plpy, document_ident):
    """Produce cnxml for the abstract by the given ``document_ident``."""
    plan = plpy.prepare("SELECT abstractid, html "
                        "FROM modules NATURAL LEFT JOIN abstracts "
                        "WHERE module_ident = $1;", ('integer',))
    result = plpy.execute(plan, (document_ident,), 1)
    try:
        abstractid, abstract = result[0]['abstractid'], result[0]['html']
    except (IndexError, KeyError):  # None returned
        # This means the document doesn't exist.
        raise ValueError("No document at ident: {}".format(document_ident))
    if abstractid is None:
        raise MissingAbstract(document_ident)

    warning_messages = None
    # Transform the abstract.
    if abstract:
        cnxml, warning_messages = transform_abstract_to_cnxml(
            abstract, document_ident, plpy)
    else:
        cnxml = None

    # Update the abstract.
    if cnxml:
        plan = plpy.prepare("UPDATE abstracts SET (abstract) = ($1) "
                            "WHERE abstractid = $2;",
                            ('text', 'integer'))
        plpy.execute(plan, (cnxml, abstractid,))
    return warning_messages


def transform_abstract_to_html(abstract, document_ident, plpy):
    """Convert abstract to html."""
    warning_messages = None
    abstract = '<document xmlns="http://cnx.rice.edu/cnxml" '\
        'xmlns:m="http://www.w3.org/1998/Math/MathML" '\
        'xmlns:md="http://cnx.rice.edu/mdml/0.4" '\
        'xmlns:bib="http://bibtexml.sf.net/" '\
        'xmlns:q="http://cnx.rice.edu/qml/1.0" '\
        'cnxml-version="0.7"><content>{}</content></document>'\
        .format(abstract)
    # Does it have a wrapping tag?
    abstract_html = cnxml_to_html(abstract)

    # Rename the containing element, because the abstract is a snippet,
    #   not a document.
    abstract_html = etree.parse(BytesIO(abstract_html), DEFAULT_XMLPARSER)
    container = abstract_html.xpath('/*')[0]  # a 'body' tag.
    container.tag = 'div'
    # Re-assign and stringify to what it should be without the fixes.
    abstract_html = etree.tostring(abstract_html)

    # Then fix up content references in the abstract.
    fixed_html, bad_refs = resolve_cnxml_urls(BytesIO(abstract_html),
                                              plpy,
                                              document_ident)
    if bad_refs:
        warning_messages = 'Invalid References (Abstract): {}' \
            .format('; '.join(bad_refs))

    return fixed_html, warning_messages


def transform_abstract_to_cnxml(abstract, document_ident, plpy):
    """Transform an html abstract to cnxml."""
    warning_messages = None
    cnxml = None

    if abstract:
        # Mark the wrapping 'div' as an identifiable data-type.
        html = etree.fromstring(abstract)
        container = html.xpath('/*')[0]
        container.attrib['data-type'] = 'abstract-wrapper'
        # Transform the abstract.
        cnxml = html_to_cnxml(html)

    # Then fix up content references in the abstract.
    if cnxml:
        cnxml, bad_refs = resolve_html_urls(BytesIO(cnxml),
                                            plpy, document_ident)
        if bad_refs:
            warning_messages = 'Invalid References (Abstract): {}' \
                .format('; '.join(bad_refs))

    # Strip the <wrapper> wrapper tag off the content.
    # The wrapper is used so that bare text can be in the abstract
    #   and still be valid xml, which is required for the reference resolver.
    start = cnxml.find('>') + 1
    end = len(cnxml) - len('</wrapper>')
    cnxml = cnxml[start:end]

    return cnxml, warning_messages


def produce_html_for_module(plpy, ident,
                            source_filename='index.cnxml',
                            destination_filenames=('index.cnxml.html',),
                            overwrite_html=False):
    """Produce an html file from a given module from specified source file.

    Produce an ``destination_filename`` (default 'index.cnxml.html') file
    for the module at ``ident`` using the ``source_filename``
    (default 'index.cnxml').

    Raises exceptions when the transform cannot be completed.

    Returns a message containing warnings and other information that
    does not effect the content, but may affect the user experience
    of it.

    """
    # BBB 14-Jan-2015 renamed - overwrite_html has been renamed overwrite
    return produce_transformed_file(plpy, ident, 'cnxml2html',
                                    source_filename,
                                    destination_filenames,
                                    overwrite=overwrite_html)


def produce_cnxml_for_module(plpy, ident,
                             source_filename='index.cnxml.html',
                             destination_filenames=('index.html.cnxml',
                                                    'index.cnxml',),
                             overwrite=False):
    """Produce a cnxml file from a given module from specified source file.

    Produce an ``destination_filename`` (default 'index.html.cnxml') file
    for the module at ``ident`` using the ``source_filename``
    (default 'index.cnxml.html').

    Raises exceptions when the transform cannot be completed.

    Returns a message containing warnings and other information that
    does not effect the content, but may affect the user experience
    of it.

    """
    return produce_transformed_file(plpy, ident, 'html2cnxml',
                                    source_filename, destination_filenames,
                                    overwrite=overwrite)


def produce_transformed_file(plpy, ident, transform_type,
                             source_filename, destination_filenames,
                             overwrite=False):
    """Produce a file from a given module source file with a specifc transform.

    Produce an ``destination_filename`` file for the module at ``ident``
    using the ``source_filename``.

    Raises exceptions when the transform cannot be completed.

    Returns a message containing warnings and other information that
    does not effect the content, but may affect the user experience
    of it.
    """
    transform_info = TRANSFORM_TYPES[transform_type]
    transformer, reference_resolver, media_type = transform_info
    plan = plpy.prepare("SELECT convert_from(file, 'utf-8') "
                        "FROM module_files "
                        "     NATURAL LEFT JOIN files "
                        "WHERE module_ident = $1 "
                        "      AND filename = $2;", ('integer', 'text'))
    result = plpy.execute(plan, (ident, source_filename,))
    try:
        content = result[0]['convert_from'][:]  # returns: (<bufferish ...>,)
    except (IndexError, KeyError):  # None returned
        raise MissingDocumentOrSource(ident, source_filename)

    # Remove destination if overwrite is True and if it exists
    plan = plpy.prepare('SELECT fileid FROM module_files '
                        'WHERE module_ident = $1 '
                        '      AND filename = ANY($2)',
                        ('integer', 'text[]'))
    file_id_rows = plpy.execute(plan, (ident, list(destination_filenames),))
    for row in file_id_rows:
        file_id = row['fileid']
        if overwrite:
            delete_module_files = plpy.prepare(
                'DELETE FROM module_files WHERE fileid = $1', ('integer',))
            plpy.execute(delete_module_files, (file_id,))
            delete_files = plpy.prepare(
                'DELETE FROM files WHERE fileid = $1', ('integer',))
            plpy.execute(delete_files, (file_id,))
        else:
            raise IndexFileExistsError(ident, destination_filenames)

    new_content = transformer(content)

    # Fix up content references to cnx-archive specific urls.
    new_content, bad_refs = reference_resolver(BytesIO(new_content),
                                               plpy, ident)

    warning_messages = None
    if bad_refs:
        warning_messages = 'Invalid References: {}' \
            .format('; '.join(bad_refs))

    # Find existing file in database before attempting to insert a new one.
    sha1 = hashlib.new('sha1', new_content).hexdigest()
    plan = plpy.prepare("SELECT fileid FROM files WHERE sha1 = $1;",
                        ('text',))
    try:
        destination_file_id = plpy.execute(plan, (sha1,))[0]['fileid']
    except IndexError:
        # Insert the cnxml into the database.
        payload = (new_content, media_type,)
        plan = plpy.prepare("INSERT INTO files (file, media_type) "
                            "VALUES ($1, $2) "
                            "RETURNING fileid;", ('bytea', 'text'))
        destination_file_id = plpy.execute(plan, payload)[0]['fileid']
    for filename in destination_filenames:
        insert_module_files = plpy.prepare(
            "INSERT INTO module_files "
            "  (module_ident, fileid, filename) "
            "  VALUES ($1, $2, $3);",
            ('integer', 'integer', 'text'))
        plpy.execute(insert_module_files,
                     (ident, destination_file_id, filename))
    return warning_messages


def transform_module_content(content, transform_type, plpy,
                             ident=None):
    """Transform content from a module."""
    transformer, reference_resolver, _ = TRANSFORM_TYPES[transform_type]

    new_content = transformer(content)

    # Fix up content references to cnx-archive specific urls.
    new_content, bad_refs = reference_resolver(BytesIO(new_content),
                                               plpy, ident)

    warning_messages = None
    if bad_refs:
        warning_messages = 'Invalid References: {}' \
            .format('; '.join(bad_refs))
    return new_content, warning_messages
