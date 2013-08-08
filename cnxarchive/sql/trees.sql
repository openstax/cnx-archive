
CREATE SEQUENCE nodeid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE trees (
    nodeid integer DEFAULT nextval('nodeid_seq'::regclass) NOT NULL,
    parent_id integer,
    document_id integer,
    title text,
    childorder integer,
    latest boolean
);

CREATE INDEX trees_nodeid_idx ON trees USING btree (nodeid);
CREATE UNIQUE INDEX trees_unique_doc_idx on trees(document_id) where parent_id is null;
