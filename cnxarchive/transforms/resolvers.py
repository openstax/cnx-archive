# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Resolver methods for fixing up references in transformed documents."""

import re
import inspect
import json

from lxml import etree

from ..utils import split_ident_hash, join_ident_hash

__all__ = (
    'MODULE_REFERENCE', 'RESOURCE_REFERENCE',
    'DOCUMENT_REFERENCE', 'BINDER_REFERENCE',
    'resolve_cnxml_urls', 'resolve_html_urls',
    )


LEGACY_PATH_REFERENCE_REGEX = re.compile(
    r'^(?:(https?://cnx.org)|(?P<legacy>https?://legacy.cnx.org))?'
    r'(/?(content/)? *'
    r'(?P<module>(m|col)\d{4,5})([/@](?P<version>([.\d]+|latest)))?)?/?'
    r'(?P<resource>[^#?][ -_.@\w\d]+)?'
    r'(?:\?collection=(?P<collection>(col\d{4,5}))'
    r'(?:[/@](?P<collection_version>([.\d]+|latest)))?)?'
    r'(?P<fragment>#?.*)?$',
    re.IGNORECASE)
PATH_REFERENCE_REGEX = re.compile(r"""
^(?:
  (https?://cnx.org)
  |
  (?P<legacy>https?://legacy.cnx.org)
  )?
(?:
  /contents/
  (?P<document>[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})
  (?:  @  (?P<version>[.\d]+)  )?
  (?:
    :
    (?P<bound_document>[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}
      (  @  \d+  )?
      )?
    )?
  )?
(?: ([.]{2})?/resources/
  (?P<resource>[0-9a-f]{40})?
  )?
(?P<fragment>.*)
""", re.IGNORECASE | re.VERBOSE)
MODULE_REFERENCE = 'module-reference'  # Used in legacy refs
RESOURCE_REFERENCE = 'resource-reference'
DOCUMENT_REFERENCE = 'document-reference'
BINDER_REFERENCE = 'binder-reference'

SQL_MODULE_ID_TO_MODULE_IDENT = ("""\
SELECT module_ident FROM modules
  WHERE module_id = $1 AND version = $2;
""", ('text', 'text'))

SQL_RESOURCE_INFO_STATEMENT = ("""\
SELECT row_to_json(row) FROM (
  SELECT fileid as id, sha1 as hash FROM files
    WHERE fileid = (SELECT fileid FROM module_files
                      WHERE module_ident = $1 AND filename = $2 )
) row;
""", ('integer', 'text'))

SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT = ("""\
SELECT uuid, module_version(major_version, minor_version) FROM latest_modules
WHERE moduleid = $1
""", ('text',))

SQL_MODULE_UUID_N_VERSION_BY_ID_AND_VERSION_STATEMENT = ("""\
SELECT uuid, module_version(major_version, minor_version) FROM modules
WHERE moduleid = $1 and version = $2
""", ('text', 'text'))

SQL_LATEST_DOCUMENT_IDENT_BY_ID = ("""\
SELECT module_ident FROM latest_modules
WHERE moduleid = $1
""", ('text',))

SQL_DOCUMENT_IDENT_BY_ID_N_VERSION = ("""\
SELECT module_ident FROM modules
WHERE moduleid = $1 and version = $2
""", ('text', 'text'))

SQL_MODULE_ID_N_VERSION_BY_UUID_STATEMENT = ("""\
SELECT moduleid, version FROM latest_modules
WHERE uuid = $1
""", ('uuid',))

SQL_MODULE_ID_N_VERSION_BY_UUID_AND_VERSION_STATEMENT = ("""\
SELECT moduleid, version FROM modules
WHERE uuid::text = $1 and module_version(major_version, minor_version) = $2
""", ('uuid', 'text'))

SQL_FILENAME_BY_SHA1_STATMENT = ("""\
SELECT mf.filename FROM module_files AS mf NATURAL JOIN files AS f
WHERE f.sha1 = $1
""", ('text',))

SQL_FILENAME_BY_SHA1_N_IDENT_STATMENT = ("""\
SELECT mf.filename FROM module_files AS mf NATURAL JOIN files AS f
WHERE f.sha1 = $1 AND module_ident = $2
""", ('text', 'integer'))


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


def parse_legacy_reference(ref):
    """Parse legacy reference into parts. Returns a tuple.

    Parse the legacy reference to a reference type and type specific value.
    A module-reference value contains the id, version and fragment.
    A resource-reference value contains resource filename.
    """
    match = LEGACY_PATH_REFERENCE_REGEX.match(ref)
    try:
        # Dictionary keyed by named groups, None values for no match
        matches = match.groupdict()
    except:  # None type
        raise ValueError("Unable to parse reference with value '{}'"
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


def parse_html_reference(ref):
    """Parse HTML cross reference.

    Parse the html reference to a reference type and type specific value.
    A document-reference value contains the ident-hash.
    A binder-reference value contains the ident-hash and possibly a document
    ident-hash.
    A resource-reference value resource filename.
    """
    match = PATH_REFERENCE_REGEX.match(ref)
    try:
        # Dictionary keyed by named groups, None values for no match
        matches = match.groupdict()
    except:  # None type
        raise ValueError("Unable to parse reference with value '{}'"
                         .format(ref))

    try:
        version = matches['version']
    except KeyError:
        version = None

    # We've got a match, but what kind of thing is it.
    if matches['legacy']:
        # Don't transform legacy urls if hostname is legacy.cnx.org
        type = None
        value = ()
    elif matches['resource']:
        type = RESOURCE_REFERENCE
        value = (matches['resource'], matches['fragment'],)
    elif matches['bound_document']:
        type = BINDER_REFERENCE
        value = (matches['document'], version, matches['bound_document'],
                 matches['fragment'],)
    elif matches['document']:
        # Note, this could also be a binder.
        type = DOCUMENT_REFERENCE
        value = (matches['document'], version, matches['fragment'],)
    else:
        type = None
        value = ()
    return type, value


class BaseReferenceResolver:

    default_namespace_name = None
    default_namespace = None

    def __init__(self, content, plpy=None, document_ident=None):
        self.content = etree.parse(content).getroot()
        self.plpy = plpy
        self.document_ident = document_ident
        self.namespaces = self.content.nsmap.copy()
        if None in self.namespaces:
            # The xpath method on an Element doesn't like 'None' namespaces.
            self.namespaces.pop(None)
            # The None namespace is redeclared below using the developer
            # defined namespace.
        self.namespaces[self.default_namespace_name] = self.default_namespace

    def __call__(self):
        messages = []
        cls = self.__class__

        def predicate(object):
            name = getattr(object, '__name__', '')
            return inspect.ismethod(object) and name.startswith('fix_')

        for name, method in inspect.getmembers(cls, predicate=predicate):
            messages.extend(method(self))
        messages = [e.message for e in messages]
        return etree.tostring(self.content), messages

    @classmethod
    def resolve_urls(cls, *args, **kwargs):
        resolver = cls(*args, **kwargs)
        return resolver()

    def apply_xpath(self, xpath):
        """Apply an XPath statement to the document."""
        return self.content.xpath(xpath, namespaces=self.namespaces)

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


class CnxmlToHtmlReferenceResolver(BaseReferenceResolver):

    default_namespace_name = 'html'
    default_namespace = 'http://www.w3.org/1999/xhtml'

    def get_uuid_n_version(self, module_id, version=None):
        if version:
            plan = self.plpy.prepare(
                *SQL_MODULE_UUID_N_VERSION_BY_ID_AND_VERSION_STATEMENT)
            args = (module_id, version)
        else:
            plan = self.plpy.prepare(
                *SQL_MODULE_UUID_N_VERSION_BY_ID_STATEMENT)
            args = (module_id,)
        try:
            result = self.plpy.execute(plan, args, 1)[0]
            uuid, version = result['uuid'], result['module_version']
        except (IndexError, KeyError):
            uuid, version = (None, None,)
        return uuid, version

    def get_resource_info(self, filename, document_id=None, version=None):
        document_ident = self.document_ident
        if document_id:
            if version:
                plan = self.plpy.prepare(
                    *SQL_DOCUMENT_IDENT_BY_ID_N_VERSION)
                try:
                    result = self.plpy.execute(plan, (document_id, version), 1)
                    document_ident = result[0]['module_ident']
                except (IndexError, KeyError):
                    raise ReferenceNotFound(
                        "Missing resource with filename '{}', "
                        "moduleid {} version {}."
                        .format(filename, document_id, version),
                        document_ident, filename)
            else:
                plan = self.plpy.prepare(
                    *SQL_LATEST_DOCUMENT_IDENT_BY_ID)
                result = self.plpy.execute(plan, (document_id,), 1)
                try:
                    document_ident = result[0]['module_ident']
                except (IndexError, KeyError):
                    raise ReferenceNotFound(
                        "Missing resource with filename '{}', "
                        "moduleid {} version {}."
                        .format(filename, document_id, version),
                        document_ident, filename)

        plan = self.plpy.prepare(*SQL_RESOURCE_INFO_STATEMENT)
        result = self.plpy.execute(plan, (document_ident, filename,), 1)
        try:
            info = result[0]['row_to_json']
        except (IndexError, KeyError):
            raise ReferenceNotFound(
                "Missing resource with filename '{}', "
                "moduleid {} version {}."
                .format(filename, document_id, version),
                document_ident, filename)
        else:
            if isinstance(info, basestring):
                info = json.loads(info)
            return info

    def get_page_ident_hash(self, page_uuid, page_version,
                            book_uuid, book_version, latest=None):
        """Return the uuid of the page and full ident_hash of the page.

        which may or may not include the book uuid depending on whether
        the page is within the book.
        """
        from cnxepub import flatten_tree_to_ident_hashes  # XXX
        from ..utils import join_ident_hash  # XXX
        plan = self.plpy.prepare(
            'SELECT tree_to_json($1, $2, FALSE)::json', ('text', 'text'))
        tree = self.plpy.execute(
            plan, (book_uuid, book_version))[0]['tree_to_json']
        if isinstance(tree, basestring):
            tree = json.loads(tree)
        pages = list(flatten_tree_to_ident_hashes(tree))
        book_ident_hash = join_ident_hash(book_uuid, book_version)
        page_ident_hash = join_ident_hash(page_uuid, page_version)
        for p_ident_hash in pages:
            p_id, p_version = split_ident_hash(p_ident_hash)
            if (p_id == page_uuid and
                    (page_version is None or
                     page_version == p_version)):
                return book_uuid, '{}:{}'.format(
                    latest and book_uuid or book_ident_hash,
                    page_ident_hash)
        # The page isn't in the given book, so only return the page.
        return page_uuid, page_ident_hash

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
                    ref_type, payload = parse_legacy_reference(filename)
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
                    elem.set(attr, '/resources/{}/{}'
                                   .format(info['hash'], filename))
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
                ref_type, payload = parse_legacy_reference(ref)
            except ValueError:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)
                continue

            if ref_type == MODULE_REFERENCE:
                module_id, version, collection_id,\
                    collection_version, url_frag = payload
                if version:
                    uuid, version = self.get_uuid_n_version(module_id, version)
                else:
                    uuid, _ = self.get_uuid_n_version(module_id)
                if uuid is None:
                    bad_references.append(
                        ReferenceNotFound("Unable to find a reference to "
                                          "'{}' at version '{}'."
                                          .format(module_id, version),
                                          self.document_ident, ref))
                    break

                ident_hash = join_ident_hash(uuid, version)
                if collection_id:
                    book_uuid, book_version = self.get_uuid_n_version(
                        collection_id, collection_version)
                    if book_uuid:
                        uuid, ident_hash = self.get_page_ident_hash(
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
                    anchor.set('href', '/resources/{}/{}'.
                                       format(info['hash'], filename))
            else:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)

        return bad_references


resolve_cnxml_urls = CnxmlToHtmlReferenceResolver.resolve_urls


class HtmlToCnxmlReferenceResolver(BaseReferenceResolver):

    default_namespace_name = 'c'
    default_namespace = 'http://cnx.rice.edu/cnxml'

    def get_resource_filename(self, hash):
        if self.document_ident is None:
            plan = self.plpy.prepare(*SQL_FILENAME_BY_SHA1_STATMENT)
            result = self.plpy.execute(plan, (hash,), 1)
        else:
            plan = self.plpy.prepare(*SQL_FILENAME_BY_SHA1_N_IDENT_STATMENT)
            result = self.plpy.execute(plan, (hash, self.document_ident,), 1)
        try:
            filename = result[0]['filename']
        except (IndexError, KeyError):
            raise ReferenceNotFound(
                "Missing resource with hash: {}".format(hash),
                self.document_ident, None)
        return filename

    def get_mid_n_version(self, id, version):
        if version:
            plan = self.plpy.prepare(
                *SQL_MODULE_ID_N_VERSION_BY_UUID_AND_VERSION_STATEMENT)
            result = self.plpy.execute(plan, (id, version), 1)
        else:
            plan = self.plpy.prepare(
                *SQL_MODULE_ID_N_VERSION_BY_UUID_STATEMENT)
            result = self.plpy.execute(plan, (id,), 1)
        try:
            module_id, version = result[0]['moduleid'], result[0]['version']
        except (IndexError, KeyError):  # None or unpack problem
            module_id, version = (None, None,)
        return module_id, version

    def fix_module_id(self):
        """Assign the module-id to the document element.

        This is something the transforms are unable to do because they lack
        this piece of information.
        """
        had_a_problem = False
        try:
            elm = self.apply_xpath('/c:document')[0]
        except IndexError:  # Empty list
            # The document doesn't have a document tag.
            # It is likely an abstract.
            return []
        if self.document_ident is not None:
            plan = self.plpy.prepare("SELECT moduleid FROM modules "
                                     "WHERE module_ident = $1", ('integer',))
            result = self.plpy.execute(plan, (self.document_ident,), 1)
            try:
                module_id = result[0]['moduleid']
            except (IndexError, KeyError):  # NoneType
                had_a_problem = True
        else:
            had_a_problem = True

        problems = []
        if had_a_problem:
            module_id = 'm00000'
            exc = ReferenceNotFound(
                "Cannot identify the current document's legacy `moduleid`.",
                self.document_ident, None)
            problems.append(exc)
        elm.set('module-id', module_id)

        return problems

    def fix_link_references(self):
        """Fix references to internal documents and resources."""
        # Catch the invalid, unparsable, etc. references.
        bad_references = []

        # Note, all c:link will have an @url. We purposely dumb down the xslt
        #   in order to make the scan here easy. Plus the xslt could never
        #   fully match and disassemble the url into the various attributes on
        #   a link tag.
        for link in self.apply_xpath('//c:link'):
            ref = link.get('url')

            if not ref or self._should_ignore_reference(ref):
                continue

            try:
                ref_type, payload = parse_html_reference(ref)
            except ValueError:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)
                continue

            # Delete the tentative attribute
            link.attrib.pop('url')

            # TODO handle #{id} refs in the url_frag, which could also contain
            #      path elements, so further parsing is necessary.

            if ref_type == DOCUMENT_REFERENCE:
                id, version, url_frag = payload
                mid, version = self.get_mid_n_version(id, version)
                if mid is None:
                    bad_references.append(
                        ReferenceNotFound("Unable to find a reference to "
                                          "'{}' at version '{}'."
                                          .format(id, version),
                                          self.document_ident, ref))
                else:
                    # Assign the document specific attributes.
                    link.attrib['document'] = mid
                    if version is not None:
                        link.attrib['version'] = version
            elif ref_type == BINDER_REFERENCE:
                id, version, bound_document, url_frag = payload
                mid, version = self.get_mid_n_version(id, version)
                if mid is None:
                    id, version, id_type = split_ident_hash(bound_document)
                    cid, cversion = self.get_mid_n_version(id, version)
                    if cid is None:
                        # Binder ref doesn't exist, but Document does.
                        # Assign the document specific attributes.
                        link.attrib['document'] = mid
                        if version is not None:
                            link.attrib['version'] = version
                    else:
                        # Process the ref as an external url.
                        url = "http://legacy.cnx.org/content/" \
                              "{}/{}/?collection={}".format(mid, version, cid)
                        if cversion is not None:
                            url = "{}/{}".format(url, cversion)
                        link.attrib['url'] = url
                else:
                    bad_references.append(
                        ReferenceNotFound("Unable to find a reference to "
                                          "'{}' at version '{}'."
                                          .format(id, version),
                                          self.document_ident, ref))
            elif ref_type == RESOURCE_REFERENCE:
                # TODO If the filename is in the url_frag, use it
                #      as the filename instead of looking it up.
                try:
                    sha1_hash, url_frag = payload
                    filename = self.get_resource_filename(sha1_hash)
                except ReferenceNotFound as exc:
                    bad_references.append(exc)
                else:
                    link.attrib['resource'] = filename
            else:
                exc = InvalidReference(self.document_ident, ref)
                bad_references.append(exc)
                # Preserve the content value...
                link.attrib['url'] = ref

        return bad_references

    def fix_media_references(self):
        """Fix references to interal resources."""
        # Catch the invalid, unparsable, etc. references.
        bad_references = []

        media_xpath = {
            '//c:media': ('longdesc',),
            '//c:image': ('src', 'thumbnail',),
            '//c:audio': ('src',),
            '//c:video': ('src',),
            '//c:java-applet': ('src',),
            '//c:flash': ('src',),
            '//c:download': ('src',),
            '//c:labview': ('src',),
            }

        for xpath, attrs in media_xpath.iteritems():
            for elem in self.apply_xpath(xpath):
                for attr in attrs:
                    ref = elem.get(attr)
                    if not ref or self._should_ignore_reference(ref):
                        continue
                    try:
                        ref_type, payload = parse_html_reference(ref)
                        sha1_hash, url_frag = payload
                    except ValueError:
                        exc = InvalidReference(self.document_ident, ref)
                        bad_references.append(exc)
                        continue
                    try:
                        filename = self.get_resource_filename(sha1_hash)
                    except ReferenceNotFound as exc:
                        bad_references.append(exc)
                    else:
                        elem.set(attr, filename)
        return bad_references


resolve_html_urls = HtmlToCnxmlReferenceResolver.resolve_urls
