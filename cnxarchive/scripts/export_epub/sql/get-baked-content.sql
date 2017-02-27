-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: id:str, version:str, context:str

SELECT f.file, f.media_type
FROM
  collated_file_associations AS cfa
  LEFT JOIN files AS f ON cfa.fileid = f.fileid
  LEFT JOIN modules AS m ON cfa.item = m.module_ident
  LEFT JOIN modules AS m2 ON cfa.context = m2.module_ident
WHERE
  m.uuid = %(id)s
  AND module_version(m.major_version, m.minor_version) = %(version)s
  AND ident_hash(m2.uuid, m2.major_version, m2.minor_version) = %(context)s;
