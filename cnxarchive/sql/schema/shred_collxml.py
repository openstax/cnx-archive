#!/usr/bin/env python
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""commandline tool for parsing collxml into a DB tree."""


from xml import sax
import sys
import psycopg2

# While the collxml files we process potentially contain many of these
# namespaces, I take advantage of the fact that almost none of the
# localnames (tags names) acutally overlap. The one case that does (title)
# actually works in our favor, since we want to treat it the same anyway.

ns = {"cnx": "http://cnx.rice.edu/cnxml",
      "cnxorg": "http://cnx.rice.edu/system-info",
      "md": "http://cnx.rice.edu/mdml",
      "col": "http://cnx.rice.edu/collxml",
      "cnxml": "http://cnx.rice.edu/cnxml",
      "m": "http://www.w3.org/1998/Math/MathML",
      "q": "http://cnx.rice.edu/qml/1.0",
      "xhtml": "http://www.w3.org/1999/xhtml",
      "bib": "http://bibtexml.sf.net/",
      "cc": "http://web.resource.org/cc/",
      "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}

NODE_INS = "INSERT INTO trees (parent_id,documentid,childorder) "\
    "SELECT %s, module_ident, %s from modules WHERE "\
    "moduleid = %s AND version = %s RETURNING nodeid"
NODE_NODOC_INS = "INSERT INTO trees (parent_id,childorder) VALUES (%s, %s) "\
    "RETURNING nodeid"
NODE_TITLE_UPD = "UPDATE trees SET title = %s FROM modules WHERE nodeid = %s "\
    "AND (documentid IS NULL "\
    "OR (documentid = module_ident AND name != %s))"

con = psycopg2.connect('dbname=repository')
cur = con.cursor()


def _do_insert(pid, cid, oid=0, ver=0):
    if oid:
        cur.execute(NODE_INS, (pid, cid, oid, ver))
        if cur.rowcount == 0:  # no documentid found
            cur.execute(NODE_NODOC_INS, (pid, cid))
    else:
        cur.execute(NODE_NODOC_INS, (pid, cid))
    res = cur.fetchall()
    if res:
        nodeid = res[0][0]
    else:
        nodeid = None
    return nodeid


def _do_update(title, nid):
    cur.execute(NODE_TITLE_UPD, (title, nid, title))


class ModuleHandler(sax.ContentHandler):
    """Handler for module link."""

    def __init__(self):
        """Create module handler with default values."""
        self.parents = [None]
        self.childorder = 0
        self.map = {}
        self.tag = u''
        self.contentid = u''
        self.version = u''
        self.title = u''
        self.nodeid = 0
        self.derivedfrom = [None]

    def startElementNS(self, (uri, localname), qname, attrs):
        """Handle element."""
        self.map[localname] = u''
        self.tag = localname

        if localname == 'module':
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1], self.childorder[-1],
                                attrs[(None, "document")],
                                attrs[(ns["cnxorg"],
                                      "version-at-this-collection-version")])
            if nodeid:
                self.nodeid = nodeid

        elif localname == 'subcollection':
            # TODO insert a metadata record into modules table for subcol.
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1], self.childorder[-1])
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'derived-from':
            self.derivedfrom.append(True)

    def characters(self, content):
        """Copy characters to tag."""
        self.map[self.tag] += content

    def endElementNS(self, (uris, localname), qname):
        """Assign local values."""
        if localname == 'content-id' and not self.derivedfrom[-1]:
            self.contentid = self.map[localname]
        elif localname == 'version' and not self.derivedfrom[-1]:
            self.version = self.map[localname]
        elif localname == 'title' and not self.derivedfrom[-1]:
            self.title = self.map[localname]
            if self.parents[-1]:  # current node is a subcollection or module
                _do_update(self.title.encode('utf-8'), self.nodeid)

        elif localname == 'derived-from':
            self.derivedfrom.pop()

        elif localname == 'metadata':
            # We know that at end of metadata, we've got the collection info
            self.childorder = [0]
            nodeid = _do_insert(None, self.childorder[-1],
                                self.contentid, self.version)
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'content':
            # this occurs at the end of each container class:
            # either colletion or subcollection
            self.parents.pop()
            self.childorder.pop()


parser = sax.make_parser()
parser.setFeature(sax.handler.feature_namespaces, 1)
parser.setContentHandler(ModuleHandler())
parser.parse(open(sys.argv[1]))

con.commit()
