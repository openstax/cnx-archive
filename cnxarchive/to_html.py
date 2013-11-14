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


__all__ = (
    'transform_collxml_to_html', 'transform_cnxml_to_html',
    'produce_html_for_collection', 'produce_html_for_module',
    'produce_html_for_collections', 'produce_html_for_modules',
    )


HTML_TEMPLATE_FOR_CNXML = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
{metadata}
{content}
</html>
"""
RHAPTOS_CNXMLUTILS_DIR = os.path.dirname(rhaptos.cnxmlutils.__file__)
XSL_DIRECTORY = os.path.abspath(os.path.join(RHAPTOS_CNXMLUTILS_DIR, 'xsl'))

SQL_MODULE_ID_TO_MODULE_IDENT = """\
SELECT module_ident FROM modules
  WHERE module_id = %s AND version = %s;
"""
SQL_RESOURCE_INFO_STATEMENT = """\
SELECT row_to_json(row) FROM (
  SELECT fileid as id, md5 as hash FROM files
    WHERE fileid = (SELECT fileid FROM module_files
                      WHERE module_ident = %s AND filename = %s )
) row;
"""
SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT = """\
SELECT uuid, version FROM modules WHERE moduleid = %s
"""
DEFAULT_ID_SELECT_QUERY = """\
SELECT module_ident FROM modules AS m
  WHERE portal_type = 'Module'
        AND NOT EXISTS (SELECT 1 FROM module_files
                          WHERE module_ident = m.module_ident
                                AND filename = 'index.html');
"""


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


PATH_REFERENCE_REGEX = re.compile(
    r'^(/?(content/)?(?P<module>(m|col)\d{5})(/(?P<version>[.\d]+))?|(?P<resource>[-.@\w\d]+))#?.*$',
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

    # We've got a match, but what kind of thing is it.
    if matches['module']:
        type = MODULE_REFERENCE
        # FIXME value[2] reserved for url fragment.
        value = (matches['module'], matches['version'], None)
    elif matches['resource']:
        type = RESOURCE_REFERENCE
        value = matches['resource']
    return type, value


class ReferenceResolver:

    def __init__(self, db_connection, document_ident, html):
        self.db_connection = db_connection
        self.document_ident = document_ident
        self.document = etree.parse(html).getroot()
        self.namespaces = self.document.nsmap.copy()
        self.namespaces['html'] = self.namespaces.pop(None)

    def __call__(self):
        messages = []
        messages.extend(self.fix_img_references())
        messages.extend(self.fix_anchor_references())
        messages = [e.message for e in messages]
        return etree.tostring(self.document), messages

    @classmethod
    def fix_reference_urls(cls, db_connection, document_ident, html):
        resolver = cls(db_connection, document_ident, html)
        return resolver()

    def get_uuid_n_version(self, module_id, version=None):
        with self.db_connection.cursor() as cursor:
            cursor.execute(SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT,
                           (module_id,))
            try:
                uuid, version = cursor.fetchone()
            except (TypeError, ValueError):  # None or unpack problem
                uuid, version = (None, None,)
        return uuid, version

    def get_resource_info(self, filename):
        with self.db_connection.cursor() as cursor:
            cursor.execute(SQL_RESOURCE_INFO_STATEMENT,
                           (self.document_ident, filename,))
            try:
                info = cursor.fetchone()[0]
            except TypeError:
                raise ReferenceNotFound(
                    "Missing resource with filename '{}'." \
                        .format(filename),
                    self.document_ident, filename)
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
                        or ref.startswith('/help')
        return should_ignore

    def fix_img_references(self):
        """Fix references to interal resources."""
        # Catch the invalid, unparsable, etc. references.
        bad_references = []

        for img in self.apply_xpath('//html:img'):
            filename = img.get('src')
            if not filename or self._should_ignore_reference(filename):
                continue

            try:
                info = self.get_resource_info(filename)
            except ReferenceNotFound as exc:
                bad_references.append(exc)
            else:
                img.set('src', '../resources/{}'.format(info['hash'],))
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
                module_id, version, url_frag = payload
                uuid, version = self.get_uuid_n_version(module_id, version)
                if uuid is None:
                    bad_references.append(
                        ReferenceNotFound("Unable to find a reference to "
                                          "'{}' at version '{}'." \
                                              .format(module_id, version),
                                          self.document_ident, ref))
                else:
                    url_frag = url_frag and url_frag or ''
                    path = '/contents/{}@{}{}'.format(uuid, version, url_frag)
                    anchor.set('href', path)
            elif ref_type == RESOURCE_REFERENCE:
                try:
                    info = self.get_resource_info(payload)
                except ReferenceNotFound as exc:
                    bad_references.append(exc)
                else:
                    anchor.set('href', '../resources/{}'.format(info['hash'],))
        return bad_references

fix_reference_urls = ReferenceResolver.fix_reference_urls


def transform_cnxml_to_html(cnxml):
    """Transforms raw cnxml content to html."""
    xml_parser = etree.XMLParser(resolve_entities=False)
    gen_xsl = lambda f: etree.XSLT(etree.parse(f))
    cnxml = etree.parse(BytesIO(cnxml), xml_parser)

    # Transform the content to html.
    cnxml_to_html_filepath = os.path.join(XSL_DIRECTORY, 'cnxml-to-html5.xsl')
    cnxml_to_html = gen_xsl(cnxml_to_html_filepath)
    content = cnxml_to_html(cnxml)

    # Transform the metadata to html.
    cnxml_to_html_metadata_filepath = os.path.join(
            XSL_DIRECTORY,
            'cnxml-to-html5-metadata.xsl')
    cnxml_to_html_metadata = gen_xsl(cnxml_to_html_metadata_filepath)
    metadata = cnxml_to_html_metadata(cnxml)

    html = HTML_TEMPLATE_FOR_CNXML.format(metadata=metadata, content=content)
    return html


def transform_collxml_to_html(collxml):
    """Transforms raw collxml content to html"""
    # XXX Temporarily return the same thing, worry about the transform
    #     after the higher level process works through.
    html = collxml
    return html


def produce_html_for_collection(db_connection, cursor, collection_ident):
    # FIXME There is a better way to join this information, but
    #       for the sake of testing scope stick with the simple yet
    #       redundant lookups.
    cursor.execute("SELECT filename, fileid FROM module_files "
                   "  WHERE module_ident = %s;", (collection_ident,))
    file_metadata = dict(cursor.fetchall())
    file_id = file_metadata['collection.xml']
    # Grab the file for transformation.
    cursor.execute("SELECT file FROM files WHERE fileid = %s;",
                   (file_id,))
    collxml = cursor.fetchone()[0]
    collxml = collxml[:]
    collection_html = transform_collxml_to_html(collxml)
    # Insert the collection.html into the database.
    payload = (memoryview(collection_html),)
    cursor.execute("INSERT INTO files (file) VALUES (%s) "
                   "RETURNING fileid;", payload)
    collection_html_file_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO module_files "
                   "  (module_ident, fileid, filename, mimetype) "
                   "  VALUES (%s, %s, %s, %s);",
                   (collection_ident, collection_html_file_id,
                    'collection.html', 'text/html',))


def produce_html_for_collections(db_connection):
    """Produce HTML files of existing collection documents. This will
    do the work on all collections in the database.

    Yields a state tuple after each collection is handled.
    The state tuple contains the id of the collection that was transformed
    and either None when no errors have occured
    or a message containing information about the issue.
    """
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT module_ident FROM modules "
                       "  WHERE portal_type = 'Collection';")
        # Note, the "ident" is different from the "id" in our tables.
        collection_idents = cursor.fetchall()

    for collection_ident in collection_idents:
        with db_connection.cursor() as cursor:
            produce_html_for_collection(db_connection, cursor, collection_ident)
        yield (collection_ident, None)

    raise StopIteration


def produce_html_for_module(db_connection, cursor, ident):
    message = None
    # FIXME There is a better way to join this information, but
    #       for the sake of testing scope stick with the simple yet
    #       redundant lookups.
    try:
        cursor.execute("SELECT filename, fileid FROM module_files "
                       "  WHERE module_ident = %s;", (ident,))
    except Exception as e:
        message = e.message
    else:
        file_metadata = dict(cursor.fetchall())
        file_id = file_metadata['index.cnxml']
        # Grab the file for transformation.
        cursor.execute("SELECT file FROM files WHERE fileid = %s;",
                       (file_id,))
        cnxml = cursor.fetchone()[0]
        cnxml = cnxml[:]
    try:
        index_html = transform_cnxml_to_html(cnxml)
    except Exception as exc:
        # TODO Log the exception in more detail.
        message = "While attempting to transform the content we ran into " \
                  "an error: " + exc.message
    else:
        # Fix up content references to cnx-archive specific urls.
        index_html, bad_refs = fix_reference_urls(db_connection, ident,
                                                  BytesIO(index_html))
        if bad_refs:
            message = 'Invalid References: {}'.format('; '.join(bad_refs))

        # Insert the index.html into the database.
        payload = (memoryview(index_html),)
        cursor.execute("INSERT INTO files (file) VALUES (%s) "
                       "RETURNING fileid;", payload)
        html_file_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO module_files "
                       "  (module_ident, fileid, filename, mimetype) "
                       "  VALUES (%s, %s, %s, %s);",
                       (ident, html_file_id,
                        'index.html', 'text/html',))
    return message


def produce_html_for_modules(db_connection,
                             id_select_query=DEFAULT_ID_SELECT_QUERY):
    """Produce HTML files of existing module documents. This will
    do the work on all modules in the database.

    Yields a state tuple after each module is handled.
    The state tuple contains the id of the module that was transformed
    and either None when no errors have occured
    or a message containing information about the issue.
    """
    with db_connection.cursor() as cursor:
        cursor.execute(id_select_query)
        # Note, the "ident" is different from the "id" in our tables.
        idents = [v[0] for v in cursor.fetchall()]

    for ident in idents:
        with db_connection.cursor() as cursor:
            message = produce_html_for_module(db_connection, cursor, ident)
        yield (ident, message)

    raise StopIteration
