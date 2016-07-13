CREATE OR REPLACE FUNCTION update_users_from_legacy ()
RETURNS TRIGGER
LANGUAGE PLPGSQL
AS '
BEGIN
UPDATE users
SET first_name = NEW.firstname,
    last_name = NEW.surname,
    full_name = NEW.fullname
WHERE username = NEW.personid;
RETURN NULL;
END;
';

CREATE TRIGGER update_users_from_legacy
  BEFORE UPDATE ON persons FOR EACH ROW
  EXECUTE PROCEDURE update_users_from_legacy();




CREATE OR REPLACE FUNCTION update_default_modules_stateid ()
RETURNS TRIGGER
LANGUAGE PLPGSQL
AS $$
BEGIN
  IF NEW.portal_type = 'Collection' THEN
    NEW.stateid = 5;
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER update_default_modules_stateid
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_default_modules_stateid();
