-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string filename:string
SELECT row_to_json(combined_rows) as module
FROM (SELECT
  m.uuid AS id,
  short_id(m.uuid) as "shortId",

  module_version(m.major_version, m.minor_version) AS current_version,
  -- can't use "version" as we need it in GROUP BY clause and it causes a
  -- "column name is ambiguous" error

  m.name, m.created as _created, m.revised as _revised,
  abstract, m.stateid, m.doctype,l.url AS license, m.module_ident AS ident, m.submitter, m.submitlog,
  p.uuid AS parent_id,

  module_version(p.major_version, p.minor_version) AS "parentVersion",

  m.authors as authors, m.licensors as licensors, m.maintainers as publishers,
  COALESCE(m.parentauthors,ARRAY(select ''::text where false)) as "parentAuthors",
  m.language as language,
  (select '{'||list(''''||roleparam||''':['''||array_to_string(personids,''',''')||''']')||'}' from
     roles natural join moduleoptionalroles where
         module_ident=m.module_ident group by module_ident) as _roles,
  list(tag) as _subject,
  convert_from(file,'utf8'),
  m.google_analytics as "googleAnalytics",
  m.print_style as "printStyle",
  m.buylink as "buyLink",
  m.moduleid as "legacy_id",
  m.version as  "legacy_version"
FROM modules m
NATURAL JOIN abstracts
JOIN licenses l on l.licenseid = m.licenseid
JOIN module_files mf on mf.module_ident = m.module_ident join files f on f.fileid = mf.fileid
LEFT JOIN modules p on m.parent = p.module_ident
LEFT JOIN moduletags mt on m.module_ident = mt.module_ident NATURAL LEFT JOIN tags
WHERE
m.uuid = %(id)s AND
 module_version(m.major_version, m.minor_version) = %(version)s AND
mf.filename = %(filename)s
GROUP BY
m.uuid, m.portal_type, current_version, m.name, m.created, m.revised, abstract, m.stateid, m.doctype,
l.url, m.module_ident, m.submitter, m.submitlog, p.uuid, "parentVersion", m.authors, m.licensors,
m.maintainers, m.parentauthors, m.language, f.file
) combined_rows;
