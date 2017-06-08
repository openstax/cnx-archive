# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Configuration for database access for archive."""

import os.path


# Configuration keys
CONNECTION_STRING = 'db-connection-string'

# Data directory and test data location
here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(here, 'tests', 'data')
TEST_DATA_SQL_FILE = os.path.join(TEST_DATA_DIRECTORY, 'data.sql')
REPOSITORY_NAME = 'OpenStax-CNX Repository'
