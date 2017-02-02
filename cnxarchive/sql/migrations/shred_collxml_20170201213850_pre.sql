-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

create  or replace function shred_collxml (doc text) returns void
as $$

from xml import sax

# While the collxml files we process potentially contain many of these
# namespaces, I take advantage of the fact that almost none of the
# localnames (tags names) acutally overlap. The one case that does (title)
# actually works in our favor, since we want to treat it the same anyway.

ns = { "cnx":"http://cnx.rice.edu/cnxml",
       "cnxorg":"http://cnx.rice.edu/system-info",
       "md":"http://cnx.rice.edu/mdml",
       "col":"http://cnx.rice.edu/collxml",
       "cnxml":"http://cnx.rice.edu/cnxml",
       "m":"http://www.w3.org/1998/Math/MathML",
       "q":"http://cnx.rice.edu/qml/1.0",
       "xhtml":"http://www.w3.org/1999/xhtml",
       "bib":"http://bibtexml.sf.net/",
       "cc":"http://web.resource.org/cc/",
       "rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#"
}

NODE_INS=plpy.prepare("INSERT INTO trees (parent_id,documentid,childorder) SELECT $1, module_ident, $2 from modules where moduleid = $3 and version = $4 returning nodeid", ("int","int","text","text"))
NODE_NODOC_INS=plpy.prepare("INSERT INTO trees (parent_id,childorder) VALUES ($1, $2) returning nodeid", ("int","int"))
NODE_TITLE_UPD=plpy.prepare("UPDATE trees set title = $1 from modules where nodeid = $2 and (documentid is null or (documentid = module_ident and name != $1))", ("text","int"))

def _do_insert(pid,cid,oid=0,ver=0):
    if oid:
        res = plpy.execute(NODE_INS,(pid,cid,oid,ver))
        if res.nrows() == 0: # no documentid found
            plpy.execute(NODE_NODOC_INS,(pid,cid))
    else:
        res = plpy.execute(NODE_NODOC_INS,(pid,cid))
    if res.nrows():
        nodeid=res[0]["nodeid"]
    else:
        nodeid = None
    return nodeid

def _do_update(title,nid):
    plpy.execute(NODE_TITLE_UPD, (title,nid))

class ModuleHandler(sax.ContentHandler):
    def __init__(self):
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
        self.map[localname] = u''
        self.tag = localname

        if localname == 'module':
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1],attrs[(None,"document")],attrs[(ns["cnxorg"],"version-at-this-collection-version")])
            if nodeid:
                self.nodeid = nodeid

        elif localname == 'subcollection':
            # TODO insert a metadata record into modules table for subcol.
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1])
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'derived-from':
            self.derivedfrom.append(True)


    def characters(self,content):
        self.map[self.tag] += content

    def endElementNS(self, (uris, localname), qname):
        if localname == 'content-id' and not self.derivedfrom[-1]:
            self.contentid = self.map[localname]
        elif localname == 'version' and not self.derivedfrom[-1]:
            self.version = self.map[localname]
        elif localname == 'title' and not self.derivedfrom[-1]:
            self.title = self.map[localname]
            if self.parents[-1]: # current node is a subcollection or module
               _do_update(self.title.encode('utf-8'), self.nodeid)

        elif localname == 'derived-from':
            self.derivedfrom.pop()

        elif localname == 'metadata':
            # We know that at end of metadata, we have got the collection info
            self.childorder = [0]
            nodeid = _do_insert(None,self.childorder[-1], self.contentid, self.version)
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'content':
            #this occurs at the end of each container class: collection or sub.
            self.parents.pop()
            self.childorder.pop()


parser = sax.make_parser()
parser.setFeature(sax.handler.feature_namespaces, 1)
parser.setContentHandler(ModuleHandler())

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
parser.parse(StringIO(doc))
$$
language plpythonu;

create or replace function shred_collxml (fid int)  returns void as
$$
select shred_collxml(convert_from(file,'UTF8')) from files where fileid = fid
$$
language sql;


create or replace function shred_collxml (fid int, docid int) returns void as
$$
select shred_collxml(convert_from(file,'UTF8')) from files where fileid = fid
    and not exists (
       select 1 from trees where documentid = docid and parent_id is null)
$$ language sql;

create or replace function shred_collxml_trigger () returns trigger as $$
BEGIN
PERFORM shred_collxml(NEW.fileid, NEW.module_ident);
RETURN NEW;
END;
$$
LANGUAGE plpgsql;

drop trigger if exists shred_collxml on module_files;

create trigger shred_collxml BEFORE INSERT on module_files
for each row when (NEW.filename = 'collection.xml') execute procedure shred_collxml_trigger ();
