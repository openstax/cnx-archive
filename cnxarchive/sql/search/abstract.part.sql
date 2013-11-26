-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
SELECT
  cm.module_ident,
  %({0})s::text ||'-::-abstract' as key
FROM
  latest_modules cm,
  abstracts a
WHERE
  cm.abstractid = a.abstractid
  AND
  a.html ~* req(%({0})s::text)
