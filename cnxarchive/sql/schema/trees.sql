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
    PRIMARY KEY (nodeid),
    FOREIGN KEY (parent_id) REFERENCES trees (nodeid)
);

-- the unique index insures only one top-level tree per document metadata
CREATE UNIQUE INDEX trees_unique_doc_idx on trees(documentid) where parent_id is null;
