CREATE AGGREGATE list ( BASETYPE = text, SFUNC = comma_cat, STYPE = text, INITCOND = '' );
CREATE AGGREGATE semilist ( BASETYPE = text, SFUNC = semicomma_cat, STYPE = text, INITCOND = '' );
