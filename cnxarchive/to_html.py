# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""
import os
import re
import json
from io import BytesIO

import rhaptos.cnxmlutils
from lxml import etree

import cnxarchive


__all__ = (
    'transform_cnxml_to_html',
    'produce_html_for_module', 'produce_html_for_abstract',
    'transform_abstract', 'transform_module_content',
    )


XML_PARSER_OPTIONS = {
    'load_dtd': True,
    'resolve_entities': True,
    'no_network': False,   # don't force loading our cnxml/DTD packages
    'attribute_defaults': False,
    }
HTML_TEMPLATE_FOR_CNXML = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
{metadata}
{content}
</html>
"""
RHAPTOS_CNXMLUTILS_DIR = os.path.dirname(rhaptos.cnxmlutils.__file__)
XSL_DIRECTORY = os.path.abspath(os.path.join(RHAPTOS_CNXMLUTILS_DIR, 'xsl'))
CNXARCHIVE_DIR = os.path.dirname(cnxarchive.__file__)
MATHML_XSL_PATH = os.path.abspath(os.path.join(
    CNXARCHIVE_DIR, 'xsl', 'content2presentation.xsl'))

SQL_MODULE_ID_TO_MODULE_IDENT = """\
SELECT module_ident FROM modules
  WHERE module_id = %s AND version = %s;
"""
SQL_RESOURCE_INFO_STATEMENT = """\
SELECT row_to_json(row) FROM (
  SELECT fileid as id, sha1 as hash FROM files
    WHERE fileid = (SELECT fileid FROM module_files
                      WHERE module_ident = %s AND filename = %s )
) row;
"""
SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT = """\
SELECT uuid, concat_ws('.', major_version, minor_version) FROM latest_modules
WHERE moduleid = %s
"""
SQL_MODULE_UUID_N_VERSION_BY_ID_AND_VERSION_STATEMENT = """\
SELECT uuid, concat_ws('.', major_version, minor_version) FROM modules
WHERE moduleid = %s and version = %s
"""

SQL_LATEST_DOCUMENT_IDENT_BY_ID = """\
SELECT module_ident FROM latest_modules
WHERE moduleid = %s
"""

SQL_DOCUMENT_IDENT_BY_ID_N_VERSION = """\
SELECT module_ident FROM modules
WHERE moduleid = %s and version = %s
"""


class MissingDocumentOrSource(Exception):
    """Used to signify that the document or source XML document
    cannot be found.
    """

    def __init__(self, document_ident, filename):
        self.document_ident = document_ident
        self.filename = filename
        msg = "Cannot find document (at ident: {}) " \
              "or file with filename '{}'." \
              .format(self.document_ident, self.filename)
        super(MissingDocumentOrSource, self).__init__(msg)


class MissingAbstract(Exception):
    """Used to signify that the abstract is missing from a document entry."""

    def __init__(self, document_ident):
        self.document_ident = document_ident
        msg = "Cannot find abstract for document (at ident: {})." \
                .format(self.document_ident)
        super(MissingAbstract, self).__init__(msg)


class BaseReferenceException(Exception):
    """Not for direct use, but used to subclass other exceptions."""

    def __init__(self, message, document_ident, reference):
        self.document_ident = document_ident
        self.reference = reference
        message = "{}: document={}, reference={}" \
                .format(message, self.document_ident, self.reference)
        super(BaseReferenceException, self).__init__(message)


class ReferenceNotFound(BaseReferenceException):
    """Used when a reference to a resource can't be found."""


class InvalidReference(BaseReferenceException):
    """Used when a reference by all known accounts appears to be invalid."""

    def __init__(self, document_ident, reference):
        msg = "Invalid reference value"
        super(InvalidReference, self).__init__(msg, document_ident, reference)


class IndexHtmlExistsError(Exception):
    """Raised when index.cnxml.html for an ident already exists but we are not
    overwriting it
    """

    def __init__(self, document_ident):
        message = 'index.cnxml.html already exists for document {}'.format(
                document_ident)
        super(IndexHtmlExistsError, self).__init__(message)


PATH_REFERENCE_REGEX = re.compile(
    r'^(?:(https?://cnx.org)|(?P<legacy>https?://legacy.cnx.org))?(/?(content/)? *'
    r'(?P<module>(m|col)\d{4,5})([/@](?P<version>([.\d]+|latest)))?)?/?'
    r'(?P<resource>[^#?][ -_.@\w\d]+)?'
    r'(?:\?collection=(?P<collection>(col\d{4,5}))(?:[/@](?P<collection_version>([.\d]+|latest)))?)?'
    r'(?P<fragment>#?.*)?$',
    re.IGNORECASE)
MODULE_REFERENCE = 'module-reference'
RESOURCE_REFERENCE = 'resource-reference'


def parse_reference(ref):
    """Parse the reference to a reference type and type specific value.
    A module-reference value contains the id, version and fragment.
    A resource-reference value resource filename.
    """
    match = PATH_REFERENCE_REGEX.match(ref)
    try:
        # Dictionary keyed by named groups, None values for no match
        matches = match.groupdict()
    except:  # None type
        raise ValueError("Unable to parse reference with value '{}'" \
                         .format(ref))

    version = matches['version']
    if version == 'latest':
        version = None
    collection_version = matches['collection_version']
    if collection_version == 'latest':
        collection_version = None

    # We've got a match, but what kind of thing is it.
    if matches['legacy']:
        # Don't transform legacy urls if hostname is legacy.cnx.org
        type = None
        value = ()
    elif matches['resource']:
        type = RESOURCE_REFERENCE
        value = (matches['resource'].strip(), matches['module'], version)
    elif matches['module']:
        type = MODULE_REFERENCE
        value = (matches['module'], version, matches['collection'],
                 collection_version, matches['fragment'])
    else:
        type = None
        value = ()
    return type, value


class ReferenceResolver:

    def __init__(self, db_connection, document_ident, html):
        self.db_connection = db_connection
        self.document_ident = document_ident
        self.document = etree.parse(html).getroot()
        self.namespaces = self.document.nsmap.copy()
        if None in self.namespaces:
            # The xpath method on an Element doesn't like 'None' namespaces.
            self.namespaces.pop(None)
            # The None namespace is assumed to be xhtml, redeclared below.
        self.namespaces['html'] = 'http://www.w3.org/1999/xhtml'

    def __call__(self):
        messages = []
        messages.extend(self.fix_media_references())
        messages.extend(self.fix_anchor_references())
        messages = [e.message for e in messages]
        return etree.tostring(self.document), messages

    @classmethod
    def fix_reference_urls(cls, db_connection, document_ident, html):
        resolver = cls(db_connection, document_ident, html)
        return resolver()

    def get_uuid_n_version(self, module_id, version=None):
        with self.db_connection.cursor() as cursor:
            if version:
                cursor.execute(SQL_MODULE_UUID_N_VERSION_BY_ID_AND_VERSION_STATEMENT,
                               (module_id, version))
            else:
                cursor.execute(SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT,
                               (module_id,))
            try:
                uuid, version = cursor.fetchone()
            except (TypeError, ValueError):  # None or unpack problem
                uuid, version = (None, None,)
        return uuid, version

    def get_resource_info(self, filename, document_id=None, version=None):
        document_ident = self.document_ident
        with self.db_connection.cursor() as cursor:
            if document_id:
                if version:
                    cursor.execute(SQL_DOCUMENT_IDENT_BY_ID_N_VERSION, [document_id, version])
                    try:
                        document_ident = cursor.fetchone()[0]
                    except TypeError:
                        raise ReferenceNotFound(
                                "Missing resource with filename '{}', moduleid {} version {}." \
                                        .format(filename, document_id, version),
                                document_ident, filename)
                else:
                    cursor.execute(SQL_LATEST_DOCUMENT_IDENT_BY_ID, [document_id])
                    try:
                        document_ident = cursor.fetchone()[0]
                    except TypeError:
                        raise ReferenceNotFound(
                                "Missing resource with filename '{}', moduleid {} version {}." \
                                        .format(filename, document_id, version),
                                document_ident, filename)

            cursor.execute(SQL_RESOURCE_INFO_STATEMENT,
                           (document_ident, filename,))
            try:
                info = cursor.fetchone()[0]
            except TypeError:
                raise ReferenceNotFound(
                    "Missing resource with filename '{}', moduleid {} version {}." \
                        .format(filename, document_id, version),
                    document_ident, filename)
            else:
                if isinstance(info, basestring):
                    info = json.loads(info)
                return info

    def apply_xpath(self, xpath):
        """Apply an XPath statement to the document."""
        return self.document.xpath(xpath, namespaces=self.namespaces)

    def _should_ignore_reference(self, ref):
        """Given an href string, determine if it should be ignored.
        For example, external links and mailto references should be ignored.
        """
        ref = ref.strip()
        should_ignore = not ref \
                        or ref.startswith('#') \
                        or ref.startswith('http') \
                        or ref.startswith('mailto') \
                        or ref.startswith('file') \
                        or ref.startswith('/help') \
                        or ref.startswith('ftp') \
                        or ref.startswith('javascript:')
        return should_ignore

    def fix_media_references(self):
        """Fix references to interal resources."""
        # Catch the invalid, unparsable, etc. references.
        bad_references = []

        media_xpath = {
                '//html:img': 'src',
                '//html:audio': 'src',
                '//html:video': 'src',
                '//html:object': 'data',
                '//html:object/html:embed': 'src',
                '//html:source': 'src',
                '//html:span': 'data-src',
                }

        for xpath, attr in media_xpath.iteritems():
            for elem in self.apply_xpath(xpath):
                filename = elem.get(attr)
                if not filename or self._should_ignore_reference(filename):
                    continue

                try:
                    ref_type, payload = parse_reference(filename)
                    filename, module_id, version = payload
                except ValueError:
                    exc = InvalidReference(self.document_ident, filename)
                    bad_references.append(exc)
                    continue

                try:
                    info = self.get_resource_info(filename, module_id, version)
                except ReferenceNotFound as exc:
                    bad_references.append(exc)
                else:
                    elem.set(attr, '/resources/{}/{}'.format(info['hash'],filename))
        return bad_references

    def fix_anchor_references(self):
        """Fix references to internal documents and resources."""
        # Catch the invalid, unparsable, etc. references.
        bad_references = []

        for anchor in self.apply_xpath('//html:a'):
            ref = anchor.get('href')
            if not ref or self._should_ignore_reference(ref):
                continue

            try:
                ref_type, payload = parse_reference(ref)
            except ValueError:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)
                continue

            if ref_type == MODULE_REFERENCE:
                module_id, version, collection_id, collection_version, url_frag = payload
                uuid, version = self.get_uuid_n_version(module_id, version)
                ident_hash = '{}@{}'.format(uuid, version)
                if uuid is None:
                    bad_references.append(
                        ReferenceNotFound("Unable to find a reference to "
                                          "'{}' at version '{}'." \
                                              .format(module_id, version),
                                          self.document_ident, ref))

                if collection_id:
                    book_uuid, book_version = self.get_uuid_n_version(
                            collection_id, collection_version)
                    if book_uuid:
                        from .views import _get_page_in_book
                        uuid, ident_hash = _get_page_in_book(
                                uuid, version, book_uuid, book_version,
                                latest=collection_version is None)
                if uuid:
                    url_frag = url_frag and url_frag or ''
                    path = '/contents/{}{}'.format(ident_hash, url_frag)
                    anchor.set('href', path)
            elif ref_type == RESOURCE_REFERENCE:
                try:
                    filename, module_id, version = payload
                    info = self.get_resource_info(filename, module_id, version)
                except ReferenceNotFound as exc:
                    bad_references.append(exc)
                else:
                    anchor.set('href', '/resources/{}/{}'.format(info['hash'],filename))
            else:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)

        return bad_references

fix_reference_urls = ReferenceResolver.fix_reference_urls


_gen_xsl = lambda f, d=XSL_DIRECTORY: etree.XSLT(etree.parse(os.path.join(d, f)))
CNXML_TO_HTML_XSL = _gen_xsl('cnxml-to-html5.xsl')
MATHML_XSL = _gen_xsl(MATHML_XSL_PATH, '.')
CNXML_TO_HTML_METADATA_XSL = _gen_xsl('cnxml-to-html5-metadata.xsl')
DEFAULT_XMLPARSER = etree.XMLParser(**XML_PARSER_OPTIONS)


def _transform_cnxml_to_html_body(xml):
    """Transform the cnxml XML (``etree.ElementTree``) content body to html.
    """
    # Tranform content MathML to presentation MathML so MathJax can display it
    xml = MATHML_XSL(xml)
    return CNXML_TO_HTML_XSL(xml)


def _transform_cnxml_to_html_metadata(xml):
    """Transform the cnxml XML (``etree.ElementTree``) metadata to html."""
    return CNXML_TO_HTML_METADATA_XSL(xml)


def transform_cnxml_to_html(cnxml, xml_parser=DEFAULT_XMLPARSER):
    """Transforms raw cnxml content to html."""
    cnxml = etree.parse(BytesIO(cnxml), xml_parser)

    # Transform the content to html.
    content = _transform_cnxml_to_html_body(cnxml)
    # Transform the metadata to html.
    metadata = _transform_cnxml_to_html_metadata(cnxml)

    html = HTML_TEMPLATE_FOR_CNXML.format(metadata=metadata, content=content)
    return html

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
        html, warning_messages = transform_abstract(abstract, db_connection,
                                                    document_ident=document_ident)
    else:
        html = None

    # Update the abstract.
    if html:
        cursor.execute("UPDATE abstracts SET (html) = (%s) "
                       "WHERE abstractid = %s;",
                       (html, abstractid,))
    return warning_messages


def transform_abstract(abstract, db_connection, document_ident=None):
    warning_messages = None
    abstract = '<document xmlns="http://cnx.rice.edu/cnxml" xmlns:m="http://www.w3.org/1998/Math/MathML" xmlns:md="http://cnx.rice.edu/mdml/0.4" xmlns:bib="http://bibtexml.sf.net/" xmlns:q="http://cnx.rice.edu/qml/1.0" cnxml-version="0.7"><content>{}</content></document>'.format(abstract)
    # Does it have a wrapping tag?
    cnxml = etree.parse(BytesIO(abstract), DEFAULT_XMLPARSER)
    abstract_html = _transform_cnxml_to_html_body(cnxml)

    # FIXME The transform should include the default html namespace.
    #       Replace the root element to include the default namespace.
    nsmap = abstract_html.getroot().nsmap.copy()
    xhtml_namespace = 'http://www.w3.org/1999/xhtml'
    nsmap[None] = xhtml_namespace
    nsmap['html'] = xhtml_namespace
    root= etree.Element('html', nsmap=nsmap)
    root.append(abstract_html.getroot())
    # FIXME This includes fixes to the xml to include the neccessary bits.
    container = abstract_html.xpath('/body')[0]
    container.tag = 'div'

    # Re-assign and stringify to what it should be without the fixes.
    abstract_html = etree.tostring(root)

    # Then fix up content references in the abstract.
    fixed_html, bad_refs = fix_reference_urls(db_connection,
                                              document_ident,
                                              BytesIO(abstract_html))

    if bad_refs:
        warning_messages = 'Invalid References (Abstract): {}' \
                .format('; '.join(bad_refs))
    # Now unwrap it and stringify again.
    nsmap.pop(None)  # xpath doesn't accept an empty namespace.
    return etree.tostring(etree.fromstring(fixed_html).xpath(
        "/html:html/html:div", namespaces=nsmap)[0]), warning_messages


def produce_html_for_module(db_connection, cursor, ident,
                            source_filename='index.cnxml',
                            overwrite_html=False):
    """Produce and 'index.cnxml.html' file for the module at ``ident``.
    Raises exceptions when the transform cannot be completed.
    Returns a message containing warnings and other information that
    does not effect the HTML content, but may affect the user experience
    of it.
    """
    cursor.execute("SELECT convert_from(file, 'utf-8') "
                   "FROM module_files "
                   "     NATURAL LEFT JOIN files "
                   "WHERE module_ident = %s "
                   "      AND filename = %s;",
                   (ident, source_filename,))
    try:
        cnxml = cursor.fetchone()[0][:]  # returns: (<bufferish ...>,)
    except TypeError:  # None returned
        raise MissingDocumentOrSource(ident, source_filename)    

    # Remove index.cnxml.html if overwrite_html is True and if it exists
    cursor.execute('SELECT fileid FROM module_files '
                   'WHERE module_ident = %s '
                   '      AND filename = %s',
                   (ident, 'index.cnxml.html'))
    index_html_id = cursor.fetchone()
    if index_html_id:
        index_html_id = index_html_id[0]
        if index_html_id:
            if overwrite_html:
                cursor.execute('DELETE FROM module_files WHERE fileid = %s',
                               (index_html_id,))
                cursor.execute('DELETE FROM files WHERE fileid = %s',
                               (index_html_id,))
            else:
                raise IndexHtmlExistsError(ident)

    index_html, warning_messages = transform_module_content(
            cnxml, db_connection, document_ident=ident)

    # Insert the index.cnxml.html into the database.
    payload = (memoryview(index_html),)
    cursor.execute("INSERT INTO files (file) VALUES (%s) "
                   "RETURNING fileid;", payload)
    html_file_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO module_files "
                   "  (module_ident, fileid, filename, mimetype) "
                   "  VALUES (%s, %s, %s, %s);",
                   (ident, html_file_id, 'index.cnxml.html', 'text/html',))
    return warning_messages


def transform_module_content(cnxml, db_connection, document_ident=None):
    warning_messages = None
    # Transform the content.
    index_html = transform_cnxml_to_html(cnxml)
    # Fix up content references to cnx-archive specific urls.
    index_html, bad_refs = fix_reference_urls(db_connection, document_ident,
                                              BytesIO(index_html))
    if bad_refs:
        warning_messages = 'Invalid References: {}' \
                .format('; '.join(bad_refs))

    return index_html, warning_messages
