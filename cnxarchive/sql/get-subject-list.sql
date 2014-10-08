-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments:
SELECT t.tagid, t.tag, lm.portal_type, COUNT(lm.module_ident)
FROM moduletags mt
    JOIN latest_modules lm ON mt.module_ident = lm.module_ident
    RIGHT JOIN tags t ON mt.tagid = t.tagid
WHERE t.scheme = 'ISKME subject'
GROUP BY t.tagid, lm.portal_type
ORDER BY t.tag;
