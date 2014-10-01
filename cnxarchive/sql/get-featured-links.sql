-- ###
-- Copyright (c) 2014, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments:

SELECT row_to_json(combined_rows) AS featured_links
FROM (SELECT
    m.uuid AS id,
    concat_ws('.', m.major_version, m.minor_version) AS version,
    m.name AS title,
    m.moduleid AS legacy_id,
    m.version AS legacy_version,
    a.html AS abstract,
    '/resources/' || f.sha1 AS "resourcePath"
FROM modules m
  LEFT JOIN abstracts a ON m.abstractid = a.abstractid
  LEFT JOIN module_files mf ON mf.module_ident = m.module_ident
  LEFT JOIN files f ON f.fileid = mf.fileid
WHERE m.featured IS NOT NULL AND mf.filename = 'featured-cover.png'
ORDER BY m.featured
) combined_rows;
