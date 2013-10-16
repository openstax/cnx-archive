-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string
SELECT row_to_json(combined_rows) as module
FROM (SELECT
  m.uuid AS id, 
  concat_ws('.', m.major_version, m.minor_version) AS current_version,
  -- can't use "version" as we need it in GROUP BY clause and it causes a
  -- "column name is ambiguous" error

  m.name as title,
  m.created as created, m.revised as revised,
  m.stateid, m.doctype,
  l.url AS license,
  m.submitter, m.submitlog, m.portal_type as "mediaType",
  a.abstract,
  p.uuid AS "parentId",
  concat_ws('.', p.major_version, p.minor_version) AS "parentVersion",

  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT id, email, firstname, othername, surname, fullname,
                title, suffix, website
         FROM users
         WHERE users.id::text = ANY (m.authors)
         ) as user_rows) as authors,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT id, email, firstname, othername, surname, fullname,
                title, suffix, website
         FROM users
         WHERE users.id::text = ANY (m.maintainers)
         ) as user_rows) as maintainers,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT id, email, firstname, othername, surname, fullname,
                title, suffix, website
         FROM users
         WHERE users.id::text = ANY (m.licensors)
         ) user_rows) as licensors,
  COALESCE(m.parentauthors,
           ARRAY(select ''::text where false)) as "parentAuthors",
  m.language as language,
  (select '{'||list(''''||roleparam||''':['''||array_to_string(personids,''',''')||''']')||'}' from roles natural join moduleoptionalroles where module_ident=m.module_ident group by module_ident) as roles,
  list(tag) as subject,
  m.google_analytics as "googleAnalytics",
  m.buylink as "buyLink",
  m.moduleid as "legacy_id",
  m.version as "legacy_version"
FROM modules m
  LEFT JOIN abstracts a on m.abstractid = a.abstractid
  LEFT JOIN modules p on m.parent = p.module_ident
  LEFT JOIN moduletags mt on m.module_ident = mt.module_ident
  NATURAL LEFT JOIN tags, licenses l
WHERE
  m.licenseid = l.licenseid AND
  m.uuid = %(id)s AND
  concat_ws('.', m.major_version, m.minor_version) = %(version)s
GROUP BY
  m.moduleid, m.portal_type, current_version, m.name, m.created, m.revised,
  a.abstract, m.stateid, m.doctype, l.url, m.module_ident, m.submitter,
  m.submitlog, p.uuid, "parentVersion", m.authors, m.licensors, m.maintainers,
  m.parentauthors, m.language, m.google_analytics
) combined_rows ;
