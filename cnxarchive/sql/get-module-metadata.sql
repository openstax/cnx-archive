-- ### 
-- Copyright (c) 2013, Rice University 
-- This software is subject to the provisions of the GNU Affero General 
-- Public License version 3 (AGPLv3). 
-- See LICENCE.txt for details. 
-- ### 
-- arguments: id:string; version:string 
SELECT row_to_json(combined_rows) AS module 
FROM   ( 
             SELECT    m.uuid                                           AS id, 
                       concat_ws('.', m.major_version, m.minor_version) AS current_version,
                       -- can't use "version" as we need it in GROUP BY clause and it causes a 
                       -- "column name is ambiguous" error 
                       m.moduleid         AS legacy_id, 
                       m.version          AS legacy_version, 
                       m.name             AS title, 
                       iso8601(m.created) AS created, 
                       iso8601(m.revised) AS revised, 
                       m.stateid, 
                       m.doctype, 
                       ( 
                              SELECT row_to_json(license) AS license 
                              FROM   ( 
                                            SELECT l.code, 
                                                   l.version, 
                                                   l.name, 
                                                   l.url ) license), 
                       ( 
                              SELECT row_to_json(submitter_row) AS submitter 
                              FROM   ( 
                                            SELECT username   AS id, 
                                                   first_name AS firstname, 
                                                   last_name  AS surname, 
                                                   full_name  AS fullname, 
                                                   title, 
                                                   suffix 
                                            FROM   users AS u 
                                            WHERE  u.username = m.submitter ) AS submitter_row) AS submitter,
                       m.submitlog, 
                       m.portal_type AS "mediaType", 
                       a.html        AS abstract, 
                       ARRAY 
                       ( 
                              SELECT row_to_json(user_rows) 
                              FROM   ( 
                                            SELECT username   AS id, 
                                                   first_name AS firstname, 
                                                   last_name  AS surname, 
                                                   full_name  AS fullname, 
                                                   title, 
                                                   suffix 
                                            FROM   users AS u 
                                            WHERE  u.username = ANY (m.authors) ) AS user_rows) AS authors,
                       ARRAY 
                       ( 
                              SELECT row_to_json(user_rows) 
                              FROM   ( 
                                            SELECT username   AS id, 
                                                   first_name AS firstname, 
                                                   last_name  AS surname, 
                                                   full_name  AS fullname, 
                                                   title, 
                                                   suffix 
                                            FROM   users AS u 
                                            WHERE  u.username = ANY (m.maintainers) ) AS user_rows) AS publishers,
                       ARRAY 
                       ( 
                              SELECT row_to_json(user_rows) 
                              FROM   ( 
                                            SELECT username   AS id, 
                                                   first_name AS firstname, 
                                                   last_name  AS surname, 
                                                   full_name  AS fullname, 
                                                   title, 
                                                   suffix 
                                            FROM   users AS u 
                                            WHERE  u.username = ANY (m.licensors) ) user_rows) AS licensors,
                       ( 
                              SELECT row_to_json(parent_row) 
                              FROM   ( 
                                            SELECT p.uuid                                           AS id,
                                                   concat_ws('.', p.major_version, p.minor_version) AS version,
                                                   p.name                                           AS title,
                                                   ARRAY 
                                                   ( 
                                                          SELECT row_to_json(user_rows) 
                                                          FROM   ( 
                                                                        SELECT username   AS id,
                                                                               first_name AS firstname,
                                                                               last_name  AS surname,
                                                                               full_name  AS fullname,
                                                                               title, 
                                                                               suffix 
                                                                        FROM   users AS u
                                                                        WHERE  u.username = ANY (m.parentauthors) ) user_rows) AS authors ) parent_row) AS parent,
                       m.language AS language,
                       ( 
                                SELECT   '{' 
                                                  ||list('''' 
                                                  ||roleparam 
                                                  ||''':[''' 
                                                  ||array_to_string(personids,''',''') 
                                                  ||''']') 
                                                  ||'}' 
                                FROM     roles NATURAL 
                                JOIN     moduleoptionalroles 
                                WHERE    module_ident=m.module_ident 
                                GROUP BY module_ident) AS roles, 
                       ARRAY 
                       ( 
                              SELECT tag 
                              FROM   moduletags AS mt NATURAL 
                              JOIN   tags 
                              WHERE  mt.module_ident = m.module_ident) AS subjects, 
                       m.google_analytics AS "googleAnalytics",
                       m.buylink AS "buyLink", 
                       m.moduleid AS "legacy_id", 
                       m.version AS "legacy_version",
                       ARRAY 
                       ( 
                              SELECT row_to_json(history_info) 
                              FROM   ( 
                                              SELECT   concat_ws('.', m1.major_version, m1.minor_version) AS version,
                                                       iso8601(m1.revised)                                AS revised,
                                                       m1.submitlog                                       AS changes,
                                                       ( 
                                                              SELECT row_to_json(publisher) AS publisher
                                                              FROM   ( 
                                                                            SELECT username   AS id,
                                                                                   first_name AS firstname,
                                                                                   last_name  AS surname,
                                                                                   full_name  AS fullname,
                                                                                   title,
                                                                                   suffix
                                                                            FROM   users AS u
                                                                            WHERE  u.username = m1.submitter ) publisher)
                                              FROM     modules m1 
                                              WHERE    m1.uuid = %(id)s 
                                              AND      m1.revised <= m.revised 
                                              ORDER BY m1.revised DESC ) history_info) AS history,
                       ARRAY 
                       ( 
                              SELECT word 
                              FROM   modulekeywords AS mk NATURAL 
                              JOIN   keywords 
                              WHERE  mk.module_ident = m.module_ident) AS keywords 
             FROM      modules m 
             LEFT JOIN abstracts a 
             ON        m.abstractid = a.abstractid 
             LEFT JOIN modules p 
             ON        m.parent = p.module_ident, 
                       licenses l 
             WHERE     m.licenseid = l.licenseid 
             AND       m.uuid = %(id)s 
             AND       concat_ws('.', m.major_version, m.minor_version) = %(version)s 
             GROUP BY  m.moduleid, 
                       m.portal_type, 
                       current_version, 
                       m.name, 
                       m.created, 
                       m.revised, 
                       a.html, 
                       m.stateid, 
                       m.doctype, 
                       l.code, 
                       l.name, 
                       l.version, 
                       l.url, 
                       m.module_ident, 
                       m.submitter, 
                       m.submitlog, 
                       p.uuid, 
                       p.major_version, 
                       p.minor_version, 
                       p.name, 
                       m.authors, 
                       m.licensors, 
                       m.maintainers, 
                       m.parentauthors, 
                       m.language, 
                       m.google_analytics ) combined_rows ;
