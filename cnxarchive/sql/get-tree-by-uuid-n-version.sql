-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments[positional]: id:string; version:string; as_collated:boolean
SELECT tree_to_json(%s, %s, %s)::json;
