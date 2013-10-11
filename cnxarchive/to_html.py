# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""
import json
import os
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
SQL_MODULE_BY_ID_STATEMENT = """\
SELECT uuid FROM modules WHERE moduleid = %s
"""
DEFAULT_ID_SELECT_QUERY = """\
SELECT module_ident FROM modules AS m
  WHERE portal_type = 'Module'
        AND NOT EXISTS (SELECT 1 FROM module_files
                          WHERE module_ident = m.module_ident
                                AND filename = 'index.html');
"""


def _split_ref(ref):
    """Returns a valid id and version from the '/<id>@<version>' syntax.
    If version is empty, 'latest' will be assigned.
    """
    ref = ref.lstrip('/')
    split_value = ref.split('@')
    try:
        id = split_value[0]
    except IndexError:
        raise ValueError("Unable find the module id for '{}'." \
                             .format(module_ref))

    try:
        version = split_value[1]
    except IndexError:
        # None'ify the version on empty string.
        version = None

    if id == '':
        raise ValueError("Missing values")

    return id, version

def get_module_uuid(db_connection, module):
    with db_connection.cursor() as cursor:
        cursor.execute(SQL_MODULE_BY_ID_STATEMENT,
                       (module,))
        uuid = None
        result = cursor.fetchone()
        if result:
            uuid=result[0]
    return uuid

def fix_reference_urls(db_connection, document_ident, html):
    """Fix the document's internal references to other documents and
    resources.

    The database connection, passed as ``db_connection`` is used to lookup
    resources by both filename and the given ``document_ident``, which is
    the document's 'module_ident' value.

    Returns a modified version of the html document.
    """
    xml = etree.parse(html)
    xml_doc = xml.getroot()

    def get_resource_info(filename):
        with db_connection.cursor() as cursor:
            cursor.execute(SQL_RESOURCE_INFO_STATEMENT,
                           (document_ident, filename,))
            info = cursor.fetchone()[0]
        if isinstance(info, basestring):
            info = json.loads(info)
        return info

    # Namespace reworking...
    namespaces = xml_doc.nsmap.copy()
    namespaces['html'] = namespaces.pop(None)

    # Fix references to resources.
    for img in xml_doc.xpath('//html:img', namespaces=namespaces):
        filename = img.get('src')
        info = get_resource_info(filename)
        img.set('src', '../resources/{}'.format(info['hash'],))

    # Fix references to documents.
    for anchor in xml_doc.xpath('//html:a', namespaces=namespaces):
        ref = anchor.get('href')
        if (ref.startswith('#') or ref.startswith('http')) \
           and not ref.startswith('/'):
            continue
        id, version = _split_ref(ref)
        # FIXME We need a better way to determine if the link is a
        #       module or resource reference. Probably some way to
        #       add an attribute in the xsl.
        #       The try & except can be removed after we fix this.
        try:
            uuid = get_module_uuid(db_connection, id)
        except TypeError:
            uuid= None
        if uuid:
            anchor.set('href', '/contents/{}@{}'.format(uuid, version))
        else:
            info = get_resource_info(ref)
            anchor.set('href', '../resources/{}'.format(info['hash'],))

    return etree.tostring(xml_doc)


def transform_cnxml_to_html(cnxml):
    """Transforms raw cnxml content to html."""
    gen_xsl = lambda f: etree.XSLT(etree.parse(f))
    cnxml = etree.parse(BytesIO(cnxml))

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
        # Fix up content references to cnx-archive specific urls.
        index_html = fix_reference_urls(db_connection, ident,
                                        BytesIO(index_html))
    except Exception as exc:
        # TODO Log the exception in more detail.
        message = exc.message
    else:
        # Insert the collection.html into the database.
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
