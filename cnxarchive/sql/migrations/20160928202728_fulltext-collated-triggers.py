# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""
CREATE OR REPLACE FUNCTION index_collated_fulltext_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT item FROM collated_fti WHERE item = NEW.item and context = NEW.context);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO collated_fti (item, context, fulltext, module_idx)
        VALUES ( NEW.item, NEW.context,_baretext, _idx_vectors );
    ELSE
      UPDATE collated_fti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE item = NEW.item and context = NEW.context;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION index_collated_fulltext_lexeme_update_trigger()
  RETURNS TRIGGER AS $$
  BEGIN

    DELETE from collated_fti_lexemes where item = NEW.item AND context = NEW.context;

    INSERT into collated_fti_lexemes (item, context, lexeme, positions)
       (with lex as (SELECT regexp_split_to_table(NEW.module_idx::text, E' \\'') as t )
       SELECT NEW.item, NEW.context,
              substring(t,1,strpos(t,E'\\':')-1),
              ('{'||substring(t,strpos(t,E'\\':')+2)||'}')::int[] from lex) ;

  RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;
            """)


def down(cursor):
    cursor.execute("""
CREATE OR REPLACE FUNCTION index_collated_fulltext_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT item, context FROM collated_fti WHERE item = NEW.item and context = NEW.context);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO collated_fti (item, context, fulltext, module_idx)
        VALUES ( NEW.item, NEW.context,_baretext, _idx_vectors );
    ELSE
      UPDATE collated_fti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE item = NEW.item and context = NEW.context;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION index_collated_fulltext_lexeme_update_trigger()
  RETURNS TRIGGER AS $$
  BEGIN

    DELETE from collated_fti_lexemes where item = NEW.item;

    INSERT into collated_fti_lexemes (item, context, lexeme, positions)
       (with lex as (SELECT regexp_split_to_table(NEW.module_idx::text, E' \\'') as t )
       SELECT NEW.item, NEW.context,
              substring(t,1,strpos(t,E'\\':')-1),
              ('{'||substring(t,strpos(t,E'\\':')+2)||'}')::int[] from lex) ;

  RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

    """)
