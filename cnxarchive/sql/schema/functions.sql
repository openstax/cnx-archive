CREATE FUNCTION uuid_generate_v4 () RETURNS uuid LANGUAGE plpythonu AS $$ import uuid; return uuid.uuid4() $$ ;
CREATE FUNCTION "comma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '','' || $2 END' LANGUAGE 'sql';

CREATE FUNCTION "semicomma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '';--;'' || $2 END' LANGUAGE 'sql';

CREATE OR REPLACE FUNCTION title_order(text) RETURNS text AS $$
begin
if lower(substr($1, 1, 4)) = 'the ' then
 return substr($1, 5);
elsif lower(substr($1,1,3)) = 'an ' then
 return substr($1,4);
elsif lower(substr($1,1,2)) = 'a ' then
 return substr($1,3);
end if;
return $1;
end;
$$ language 'plpgsql' immutable;


CREATE OR REPLACE FUNCTION short_id (u uuid) RETURNS text as $$
select substring(replace(replace(replace(encode(uuid_send(u),'base64'),'+','-'),'/','_'),'=',''),1,8) $$
IMMUTABLE STRICT LANGUAGE SQL;


CREATE OR REPLACE FUNCTION req(text) RETURNS text AS $$
select regexp_replace($1,E'([.()?[\\]\\{}*+|])',E'\\\\\\1','g')
$$ language sql immutable;

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYELEMENT)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS $$
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYARRAY)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS $$
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i:i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
$$;




-- Deprecated (3-Feb-2015) Use html_abstract(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_abstract, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_abstract(abstract text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_abstract(<module_ident>')
  from cnxarchive.transforms import transform_abstract_to_html
  html_abstract, warning_messages = transform_abstract_to_html(abstract, None, plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_abstract(module_ident int)
  RETURNS text
AS $$
  from cnxarchive.transforms import transform_abstract_to_html
  plan = plpy.prepare("SELECT abstract FROM modules NATURAL JOIN abstracts WHERE module_ident = $1", ('integer',))
  abstract = plpy.execute(plan, (module_ident,))[0]['abstract']
  html_abstract, warning_messages = transform_abstract_to_html(abstract, module_ident, plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_abstract
$$ LANGUAGE plpythonu;

-- Deprecated (3-Feb-2015) Use html_content(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_content, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_content(cnxml text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_content(<module_ident>')
  from cnxarchive.transforms import transform_module_content
  html_content, warning_messages = transform_module_content(cnxml, 'cnxml2html', plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_content
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_content(module_ident int)
  RETURNS text
AS $$
  from cnxarchive.transforms import transform_module_content
  plan = plpy.prepare("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = $1 AND (filename = 'index.cnxml' OR filename = 'index.html.cnxml')", ('integer',))
  cnxml = plpy.execute(plan, (module_ident,))[0]['convert_from']
  content, warning_messages = transform_module_content(cnxml, 'cnxml2html', plpy, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;


CREATE OR REPLACE FUNCTION cnxml_abstract(module_ident int)
  RETURNS text
AS $$
  from cnxarchive.transforms import transform_abstract_to_cnxml
  plan = plpy.prepare("SELECT html FROM modules NATURAL JOIN abstracts WHERE module_ident = $1", ('integer',))
  abstract = plpy.execute(plan, (module_ident,))[0]['html']
  cnxml_abstract, warning_messages = transform_abstract_to_cnxml(abstract, module_ident, plpy)
  if warning_messages:
      plpy.warning(warning_messages)
  return cnxml_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION cnxml_content(module_ident int)
  RETURNS text
AS $$
  from cnxarchive.transforms import transform_module_content
  plan = plpy.prepare("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = $1 AND filename = 'index.cnxml.html'", ('integer',))
  html = plpy.execute(plan, (module_ident,))[0]['convert_from']
  content, warning_messages = transform_module_content(html, 'html2cnxml', plpy, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION strip_html(html_text TEXT)
  RETURNS text
AS $$
  import re
  return re.sub('<[^>]*?>', '', html_text, re.MULTILINE)
$$ LANGUAGE plpythonu IMMUTABLE;
