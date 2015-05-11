-- ###
-- Copyright (c) 2015, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments:

SELECT row_to_json(combined_rows) AS licenses
FROM (
  SELECT name, url, code, version,
         is_valid_for_publication AS "isValidForPublication"
  FROM licenses
  WHERE licenseid > 0
) combined_rows;
