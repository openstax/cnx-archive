-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string filename:string
SELECT row_to_json(combined_rows) as module
FROM (SELECT
  m.uuid AS id, m.version, m.name, m.created as _created, m.revised as _revised,
  abstract, m.stateid, m.doctype,l.url AS license, m.module_ident AS ident, m.submitter, m.submitlog,
  p.uuid AS parent_id, p.version AS parent_version,
  m.authors as authors, m.licensors as licensors, m.maintainers as maintainers,
  COALESCE(m.parentauthors,ARRAY(select ''::text where false)) as "parentAuthors",
  m.language as language,
  (select '{'||list(''''||roleparam||''':['''||array_to_string(personids,''',''')||''']')||'}' from
     roles natural join moduleoptionalroles where
         module_ident=m.module_ident group by module_ident) as _roles,
  list(tag) as _subject,
  encode(file,'escape'),
  m.google_analytics as "googleAnalytics"
FROM modules m
NATURAL JOIN abstracts
JOIN licenses l on l.licenseid = m.licenseid
JOIN module_files mf on mf.module_ident = m.module_ident join files f on f.fileid = mf.fileid
LEFT JOIN modules p on m.parent = p.module_ident
LEFT JOIN moduletags mt on m.module_ident = mt.module_ident NATURAL LEFT JOIN tags
WHERE
m.uuid = %(id)s AND
m.version = %(version)s AND
mf.filename = %(filename)s
GROUP BY
m.uuid, m.portal_type, m.version, m.name, m.created, m.revised, abstract, m.stateid, m.doctype,
l.url, m.module_ident, m.submitter, m.submitlog, p.uuid, p.version, m.authors, m.licensors,
m.maintainers, m.parentauthors, m.language, f.file
) combined_rows;
