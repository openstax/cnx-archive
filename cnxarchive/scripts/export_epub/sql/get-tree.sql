-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: id:str, version:str

SELECT tree_to_json(%(id)s, %(version)s, %(baked)s)::json;
