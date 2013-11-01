-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
CREATE TABLE "persons" (
  "personid" text PRIMARY KEY,
  "honorific" text,
  "firstname" text,
  "othername" text,
  "surname" text,
  "lineage" text,
  "fullname" text,
  "email" text,
  "homepage" text,
  "comment" text
);

CREATE INDEX person_firstname_upper_idx on persons (upper(firstname));
CREATE INDEX person_surname_upper_idx on persons (upper(surname));
CREATE INDEX person_personid_upper_idx on persons (upper(personid));
CREATE INDEX person_email_upper_idx on persons (upper(email));


CREATE VIEW users AS
  SELECT persons.personid AS id,
         persons.email,
         persons.firstname,
         persons.othername,
         persons.surname,
         persons.fullname,
         persons.honorific AS title,
         persons.lineage AS suffix,
         persons.homepage AS website
  FROM persons;
