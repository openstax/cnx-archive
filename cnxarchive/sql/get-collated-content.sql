-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments[positional]: ident_hash:string; context_ident_hash:string
SELECT f.file
FROM collated_file_associations AS cfa
  NATURAL JOIN files AS f,
               modules AS context,
               modules AS item
WHERE cfa.context = context.module_ident AND
      cfa.item = item.module_ident AND
      item.uuid || '@' || module_version(item.major_version, item.minor_version) = %s AND
      context.uuid || '@' || module_version(context.major_version, context.minor_version) = %s
