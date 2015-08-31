-- ###
-- Copyright (c) 2015, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

INSERT INTO service_states (id, name, default_priority, default_message)
VALUES (1, 'Maintenance', 1,
        'This site is scheduled to be down for maintaince, please excuse the interuption. Thank you.');
INSERT INTO service_states (id, name, default_priority, default_message)
VALUES (2, 'Notice', 5,
        'We are currently experiencing a high number of site wide errors. Please be patient while we look into the issue. Thank you.');
SELECT pg_catalog.setval('service_states_id_seq', 2, false);
