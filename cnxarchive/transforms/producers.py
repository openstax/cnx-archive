# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Producer functions that wrap basic transforms to create complete docs."""

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


def produce_html_for_abstract(db_connection, cursor, document_ident):
    """Produce html for the abstract by the given ``document_ident``."""
    cursor.execute("SELECT abstractid, abstract "
                   "FROM modules NATURAL LEFT JOIN abstracts "
                   "WHERE module_ident = %s;",
                   (document_ident,))
    try:
        abstractid, abstract = cursor.fetchone()
    except TypeError:  # None returned
        # This means the document doesn't exist.
        raise ValueError("No document at ident: {}".format(document_ident))
    if abstractid is None:
        raise MissingAbstract(document_ident)

    warning_messages = None
    # Transform the abstract.
    if abstract:
        html, warning_messages = transform_abstract_to_html(
            abstract, document_ident, db_connection)
    else:
        html = None

    # Update the abstract.
    if html:
        cursor.execute("UPDATE abstracts SET (html) = (%s) "
                       "WHERE abstractid = %s;",
                       (html, abstractid,))
    return warning_messages


def produce_cnxml_for_abstract(db_connection, cursor, document_ident):
    """Produce cnxml for the abstract by the given ``document_ident``."""
    cursor.execute("SELECT abstractid, html "
                   "FROM modules NATURAL LEFT JOIN abstracts "
                   "WHERE module_ident = %s;",
                   (document_ident,))
    try:
        abstractid, abstract = cursor.fetchone()
    except TypeError:  # None returned
        # This means the document doesn't exist.
        raise ValueError("No document at ident: {}".format(document_ident))
    if abstractid is None:
        raise MissingAbstract(document_ident)

    warning_messages = None
    # Transform the abstract.
    if abstract:
        cnxml, warning_messages = transform_abstract_to_cnxml(
            abstract, document_ident, db_connection)
    else:
        cnxml = None

    # Update the abstract.
    if cnxml:
        cursor.execute("UPDATE abstracts SET (abstract) = (%s) "
                       "WHERE abstractid = %s;",
                       (cnxml, abstractid,))
    return warning_messages


def transform_abstract_to_html(abstract, document_ident, db_connection):
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
                                              db_connection,
                                              document_ident)
    if bad_refs:
        warning_messages = 'Invalid References (Abstract): {}' \
            .format('; '.join(bad_refs))

    return fixed_html, warning_messages


def transform_abstract_to_cnxml(abstract, document_ident, db_connection):
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
                                            db_connection, document_ident)
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


def produce_html_for_module(db_connection, cursor, ident,
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
    return produce_transformed_file(cursor, ident, 'cnxml2html',
                                    source_filename,
                                    destination_filenames,
                                    overwrite=overwrite_html)


def produce_cnxml_for_module(db_connection, cursor, ident,
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
    return produce_transformed_file(cursor, ident, 'html2cnxml',
                                    source_filename, destination_filenames,
                                    overwrite=overwrite)


def produce_transformed_file(cursor, ident, transform_type,
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
    transformer, reference_resolver, mimetype = TRANSFORM_TYPES[transform_type]
    cursor.execute("SELECT convert_from(file, 'utf-8') "
                   "FROM module_files "
                   "     NATURAL LEFT JOIN files "
                   "WHERE module_ident = %s "
                   "      AND filename = %s;",
                   (ident, source_filename,))
    try:
        content = cursor.fetchone()[0][:]  # returns: (<bufferish ...>,)
    except TypeError:  # None returned
        raise MissingDocumentOrSource(ident, source_filename)

    # Remove destination if overwrite is True and if it exists
    cursor.execute('SELECT fileid FROM module_files '
                   'WHERE module_ident = %s '
                   '      AND filename = ANY(%s)',
                   (ident, list(destination_filenames),))
    file_id_rows = cursor.fetchall()
    for row in file_id_rows:
        file_id = row[0]
        if overwrite:
            cursor.execute('DELETE FROM module_files WHERE fileid = %s',
                           (file_id,))
            cursor.execute('DELETE FROM files WHERE fileid = %s',
                           (file_id,))
        else:
            raise IndexFileExistsError(ident, destination_filenames)

    new_content = transformer(content)

    # Fix up content references to cnx-archive specific urls.
    new_content, bad_refs = reference_resolver(BytesIO(new_content),
                                               cursor.connection, ident)

    warning_messages = None
    if bad_refs:
        warning_messages = 'Invalid References: {}' \
            .format('; '.join(bad_refs))

    # Insert the cnxml into the database.
    payload = (memoryview(new_content),)
    cursor.execute("INSERT INTO files (file) VALUES (%s) "
                   "RETURNING fileid;", payload)
    destination_file_id = cursor.fetchone()[0]
    for filename in destination_filenames:
        cursor.execute("INSERT INTO module_files "
                       "  (module_ident, fileid, filename, mimetype) "
                       "  VALUES (%s, %s, %s, %s);",
                       (ident, destination_file_id,
                        filename, mimetype,))
    return warning_messages


def transform_module_content(content, transform_type, db_connection,
                             ident=None):
    """Transform content from a module."""
    transformer, reference_resolver, _ = TRANSFORM_TYPES[transform_type]

    new_content = transformer(content)

    # Fix up content references to cnx-archive specific urls.
    new_content, bad_refs = reference_resolver(BytesIO(new_content),
                                               db_connection, ident)

    warning_messages = None
    if bad_refs:
        warning_messages = 'Invalid References: {}' \
            .format('; '.join(bad_refs))
    return new_content, warning_messages
