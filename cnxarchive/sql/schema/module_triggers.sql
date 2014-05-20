CREATE SEQUENCE collectionid_seq;

CREATE OR REPLACE FUNCTION public.moduleid_and_version_default()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
IF NEW.moduleid is NULL THEN
    CASE NEW.portal_type
       WHEN 'Collection' THEN
            select into NEW.moduleid 'col' || nextval('collectionid_seq')::text;
       ELSE
            select into NEW.moduleid 'm' || nextval('moduleid_seq')::text;
    END CASE;
ELSE
    CASE NEW.portal_type
       WHEN 'Collection' THEN
            select setval('collectionid_seq', max(substr(moduleid,4)::int) from 
            (SELECT  moduleid from modules where portal_type = 'Collection' 
             UNION ALL
             SELECT NEW.moduleid) alltogether;
       ELSE
            select setval('moduleid_seq', max(substr(moduleid,2)::int) from 
            (SELECT moduleid from modules where portal_type = 'Module'
             UNION ALL 
             SELECT NEW.moduleid) alltogether;
    END CASE;
END IF;

IF NEW.version IS NULL THEN
     NEW.version = '1.' || NEW.major_version::text;
END IF;

RETURN NEW;
END
$function$
;

-- CREATE TRIGGER module_defaults BEFORE INSERT ON modules FOR EACH ROW EXECUTE PROCEDURE moduleid_and_version_default();


