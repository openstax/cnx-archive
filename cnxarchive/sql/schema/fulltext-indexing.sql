-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

CREATE EXTENSION IF NOT EXISTS plxslt;

CREATE OR REPLACE FUNCTION xml_to_baretext(xml) RETURNS xml AS $$
<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:cnx="http://cnx.rice.edu/cnxml"
                xmlns:m="http://www.w3.org/1998/Math/MathML"
                xmlns:md="http://cnx.rice.edu/mdml/0.4"
                xmlns="http://www.w3.org/1999/xhtml"
                xmlns:bib="http://bibtexml.sf.net/"
                >

  <xsl:output format="text" omit-xml-declaration="yes"/>

  <xsl:template match="/">
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="md:*"/>

</xsl:stylesheet>
$$ LANGUAGE xslt;


CREATE OR REPLACE FUNCTION index_fulltext_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT module_ident FROM modulefti WHERE module_ident = NEW.module_ident);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO modulefti (module_ident, fulltext, module_idx)
        VALUES ( NEW.module_ident, _baretext, _idx_vectors );
    ELSE
      UPDATE modulefti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE module_ident = NEW.module_ident;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_fulltext ON module_files;
CREATE TRIGGER index_fulltext
  AFTER INSERT OR UPDATE ON module_files
    FOR EACH row WHEN (NEW.filename = 'index.cnxml.html')
      EXECUTE PROCEDURE index_fulltext_trigger();

CREATE OR REPLACE FUNCTION index_fulltext_upsert_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
  BEGIN

    IF NEW.fulltext IS NOT NULL THEN
        RETURN NEW;
    END IF;

    has_existing_record := (SELECT module_ident FROM modulefti WHERE module_ident = NEW.module_ident);

    IF has_existing_record IS NULL THEN
      INSERT INTO modulefti (module_ident, module_idx)
        VALUES ( NEW.module_ident, NEW.module_idx);
    ELSE
      UPDATE modulefti SET (module_idx) = ( NEW.module_idx)
        WHERE module_ident = NEW.module_ident;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_fulltext_upsert ON modulefti;
CREATE TRIGGER index_fulltext_upsert
  BEFORE INSERT ON modulefti
    FOR EACH row
      EXECUTE PROCEDURE index_fulltext_upsert_trigger();

