-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- Trees table contains structure of a collection, with pointers into the documents table
CREATE SEQUENCE nodeid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE trees (
    nodeid integer DEFAULT nextval('nodeid_seq'::regclass) NOT NULL,
    parent_id integer,
    documentid integer, -- foreign key documents (documentid),
    title text, -- override title
    childorder integer, -- position within parent node
    latest boolean, -- is this node supposed to track upstream changes
    is_collated boolean DEFAULT FALSE,
    PRIMARY KEY (nodeid),
    FOREIGN KEY (parent_id) REFERENCES trees (nodeid) ON DELETE CASCADE
);

-- the unique index insures only two top-level trees per document metadata - raw and collated
CREATE UNIQUE INDEX trees_unique_doc_idx on trees(documentid, is_collated) where parent_id is null;
CREATE INDEX trees_doc_idx on trees(documentid);
