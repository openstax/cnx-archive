-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

CREATE ROLE cnxarchive SUPERUSER;
ALTER ROLE cnxarchive PASSWORD 'cnxarchive';
CREATE DATABASE cnxarchive;
