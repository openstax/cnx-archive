CREATE OR REPLACE FUNCTION uuid2base64 (identifier uuid)
  RETURNS character(24)
AS $$
  from cnxarchive.utils import uuid2base64
  return uuid2base64(identifier)
$$ LANGUAGE plpythonu;



