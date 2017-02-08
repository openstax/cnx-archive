-- ###
-- Copyright (c) 2016, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- #! args:: id:str, version:str

SELECT row_to_json(combined_rows)
FROM
(SELECT
   m.uuid as id,
   module_version( m.major_version, m.minor_version) as version,
   m.name as title,
   m.language,
   m.submitter AS publisher,
   m.submitlog AS publication_message,
   iso8601(m.created) AS created, iso8601(m.revised) AS revised,
   l.url AS license_url,
   l.name as license_text,
   a.html AS summary,
   ARRAY(SELECT tag FROM moduletags AS mt NATURAL JOIN tags WHERE mt.module_ident = m.module_ident) AS subjects,
   ARRAY(SELECT word FROM modulekeywords AS mk NATURAL JOIN keywords WHERE mk.module_ident = m.module_ident) AS keywords,
   ident_hash(m.uuid, m.major_version, m.minor_version) AS "cnx-archive-uri",
   short_ident_hash(m.uuid, m.major_version, m.minor_version) AS "cnx-archive-shortid",
   -- People
   ARRAY(SELECT row_to_json(user_rows) FROM
         (SELECT username AS id, first_name AS firstname, last_name AS surname,
                 full_name as name, title, suffix, 'cnx-id' as type
          FROM users AS u
          WHERE u.username = ANY (m.authors)
          ORDER BY idx(m.authors, u.username)
          ) AS user_rows) AS authors,
   ARRAY(SELECT row_to_json(user_rows) FROM
         (SELECT username AS id, first_name AS firstname, last_name AS surname,
                 full_name as name, title, suffix, 'cnx-id' as type
          FROM users AS u
          WHERE u.username = ANY (SELECT unnest(mor.personids) FROM moduleoptionalroles AS mor WHERE mor.module_ident = m.module_ident AND mor.roleid = 3)
          ) AS user_rows) AS editors,
   '{}'::text[] AS illustrators,
    ARRAY(SELECT row_to_json(user_rows) FROM
         (SELECT username AS id, first_name AS firstname, last_name AS surname,
                 full_name as name, title, suffix, 'cnx-id' as type
          FROM users AS u
          WHERE u.username = ANY (SELECT unnest(mor.personids) FROM moduleoptionalroles AS mor WHERE mor.module_ident = m.module_ident AND mor.roleid = 4)
          ) AS user_rows) AS translators,
   ARRAY(SELECT row_to_json(user_rows) FROM
         (SELECT username AS id, first_name AS firstname, last_name AS surname,
                 full_name as name, title, suffix, 'cnx-id' as type
          FROM users AS u
          WHERE u.username = ANY (m.maintainers)
          ORDER BY idx(m.maintainers, u.username)
          ) AS user_rows) AS publishers,
   ARRAY(SELECT row_to_json(user_rows) FROM
         (SELECT username AS id, first_name AS firstname, last_name AS surname,
                 full_name as name, title, suffix, 'cnx-id' as type
          FROM users AS u
          WHERE u.username = ANY (m.licensors)
          ORDER BY idx(m.licensors, u.username)
          ) AS user_rows) AS copyright_holders,
   -- Print style
   m.print_style,
   -- Derivation 
   ident_hash(p.uuid, p.major_version, p.minor_version) AS derived_from_uri,
   p.name AS derived_from_title
 FROM
    modules AS m
    LEFT JOIN abstracts AS a ON m.abstractid = a.abstractid
    LEFT JOIN modules AS p ON m.parent = p.module_ident,
    licenses AS l
 WHERE
   m.licenseid = l.licenseid
   AND m.uuid = %(id)s
   AND module_version(m.major_version, m.minor_version) = %(version)s
) AS combined_rows;
