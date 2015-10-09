CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 uuid, identifier2 uuid)
  RETURNS BOOLEAN
AS $$
  from cnxarchive.utils import identifiers_equal
  return identifiers_equal(identifier1,identifier2)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 text, identifier2 uuid)
  RETURNS BOOLEAN
AS $$
  from cnxarchive.utils import identifiers_equal
  return identifiers_equal(identifier1,identifier2)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 uuid, identifier2 text)
  RETURNS BOOLEAN
AS $$
  from cnxarchive.utils import identifiers_equal
  return identifiers_equal(identifier1,identifier2)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION identifiers_equal (identifier1 text, identifier2 text)
  RETURNS BOOLEAN
AS $$
  from cnxarchive.utils import identifiers_equal
  return identifiers_equal(identifier1,identifier2)
$$ LANGUAGE plpythonu;

