-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###
-- arguments: id:string query:string
SELECT
  ts_headline(mfti.fulltext, plainto_tsquery(%(query)s),
              'StartSel=<b>, StopSel=</b>, ShortWord=5, MinWords=50, MaxWords=60') as headline,
  ts_headline(mfti.fulltext, plainto_tsquery(%(query)s),
         'StartSel=<b>, StopSel=</b>, MinWords=600, MaxWords=700') as fulltext
FROM
  modules as lm,
  modulefti as mfti
WHERE
  lm.uuid = %(id)s::uuid
  AND
  lm.module_ident = mfti.module_ident
