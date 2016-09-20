-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; version:string
SELECT row_to_json(combined_rows) AS module
FROM (SELECT
  m.uuid AS id,
  short_id(m.uuid) as "shortId",
  module_version(m.major_version, m.minor_version) AS current_version,
  -- can't use "version" as we need it in GROUP BY clause and it causes a
  -- "column name is ambiguous" error

  m.moduleid AS legacy_id,
  m.version AS legacy_version,
  m.name AS title,
  iso8601(m.created) AS created, iso8601(m.revised) AS revised,
  m.stateid, m.doctype,
  (SELECT row_to_json(license) AS license FROM (
        SELECT l.code, l.version, l.name, l.url
    ) license),
  (SELECT row_to_json(submitter_row) AS submitter FROM
        (SELECT username AS id, first_name AS firstname, last_name AS surname,
                full_name as fullname, title, suffix
         FROM users AS u
         WHERE u.username = m.submitter
         ) AS submitter_row) as submitter,
  m.submitlog, m.portal_type AS "mediaType",
  a.html AS abstract,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT username AS id, first_name AS firstname, last_name AS surname,
                full_name as fullname, title, suffix
         FROM users AS u
         WHERE u.username = ANY (m.authors)
         ORDER BY idx(m.authors, u.username)
         ) AS user_rows) AS authors,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT username AS id, first_name AS firstname, last_name AS surname,
                full_name as fullname, title, suffix
         FROM users AS u
         WHERE u.username = ANY (m.maintainers)
         ORDER BY idx(m.maintainers, u.username)
         ) AS user_rows) AS publishers,
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT username AS id, first_name AS firstname, last_name AS surname,
                full_name as fullname, title, suffix
         FROM users AS u
         WHERE u.username = ANY (m.licensors)
         ORDER BY idx(m.licensors, u.username)
         ) AS user_rows) AS licensors,
  p.uuid AS "parentId",
  module_version(p.major_version, p.minor_version) AS "parentVersion",
  p.name as "parentTitle",
  ARRAY(SELECT row_to_json(user_rows) FROM
        (SELECT username AS id, first_name AS firstname,
                               last_name AS surname,
                               full_name as fullname, title, suffix
         FROM users
         WHERE users.username::text = ANY (m.parentauthors)
         ORDER BY idx(m.parentauthors, users.username)
         ) AS user_rows) as "parentAuthors",
  (SELECT row_to_json(parent_row)
   FROM (
     SELECT p.uuid AS id,
            short_id(p.uuid) as "shortId",
            module_version(p.major_version, p.minor_version) AS version,
            p.name AS title,
            ARRAY(SELECT row_to_json(user_rows)
                  FROM (SELECT username AS id, first_name AS firstname,
                               last_name AS surname,
                               full_name as fullname, title, suffix
                        FROM users AS u
                        WHERE u.username = ANY (m.parentauthors)
                        ORDER BY idx(m.parentauthors, u.username)
                  ) AS user_rows) AS authors
         ) parent_row) AS parent,
  m.language AS language,
  (select '{'||list(''''||roleparam||''':['''||array_to_string(personids,''',''')||''']')||'}' from roles natural join moduleoptionalroles where module_ident=m.module_ident group by module_ident) AS roles,
  ARRAY(SELECT tag FROM moduletags AS mt NATURAL JOIN tags WHERE mt.module_ident = m.module_ident) AS subjects,
  m.google_analytics AS "googleAnalytics",
  m.buylink AS "buyLink",
  m.moduleid AS "legacy_id",
  m.version AS "legacy_version",
  ARRAY(
    SELECT row_to_json(history_info) FROM (
        SELECT module_version(m1.major_version, m1.minor_version) AS version,
            iso8601(m1.revised) AS revised, m1.submitlog AS changes,
            (SELECT row_to_json(publisher) AS publisher
             FROM (
               SELECT
                 username AS id, first_name AS firstname, last_name AS surname,
                 full_name as fullname, title, suffix
               FROM users AS u
               WHERE u.username = m1.submitter
               ) publisher)
            FROM modules m1 WHERE m1.uuid = %(id)s AND m1.revised <= m.revised
            ORDER BY m1.revised DESC
    ) history_info) AS history,
  ARRAY(SELECT word FROM modulekeywords AS mk NATURAL JOIN keywords WHERE mk.module_ident = m.module_ident) AS keywords,
  ARRAY(
    SELECT row_to_json(module_file_row) FROM (
      SELECT mf.filename AS filename, f.media_type AS media_type, f.sha1 AS id
      FROM module_files AS mf NATURAL JOIN files AS f
      WHERE mf.module_ident = m.module_ident
      ORDER BY f.sha1, f.media_type, mf.filename
    ) AS module_file_row) AS resources,
  m.print_style AS "printStyle"
FROM modules m
  LEFT JOIN abstracts a on m.abstractid = a.abstractid
  LEFT JOIN modules p on m.parent = p.module_ident,
  licenses l
WHERE
  m.licenseid = l.licenseid AND
  m.uuid = %(id)s AND
  module_version(m.major_version, m.minor_version) = %(version)s
GROUP BY
  m.moduleid, m.portal_type, current_version, m.name, m.created, m.revised,
  a.html, m.stateid, m.doctype, l.code, l.name, l.version, l.url,
  m.module_ident, m.submitter, m.submitlog, p.uuid, p.major_version,
  p.minor_version, p.name, m.authors,
  m.licensors, m.maintainers, m.parentauthors, m.language, m.google_analytics
) combined_rows ;
