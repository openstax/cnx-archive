-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments[positional]: ident_hash:string; context_ident_hash:string
SELECT f.file
FROM files AS f
  LEFT JOIN collated_file_associations cfa ON cfa.fileid = f.fileid
  LEFT JOIN modules m ON m.module_ident = cfa.item
  LEFT JOIN modules context ON context.module_ident = cfa.context
WHERE m.uuid || '@' || concat_ws('.', m.major_version, m.minor_version) = %s AND
      context.uuid || '@' || concat_ws('.', context.major_version, context.minor_version) = %s
