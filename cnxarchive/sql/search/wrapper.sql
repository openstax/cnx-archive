-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
SELECT
  module_ident,
  count(*)*{0} as weight,
  semilist(key) as keys
FROM (
  {1}
) cm
GROUP BY cm.module_ident
