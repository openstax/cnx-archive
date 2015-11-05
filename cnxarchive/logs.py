# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import os.path
import logging
import socket


__all__ = (
    'DEFAULT_LOGGING_CONFIG_FILEPATH', 'LOGGER_NAME',
    'logger', 'ContextFilter',
    )

here = os.path.abspath(os.path.dirname(__file__))
DEFAULT_LOGGING_CONFIG_FILEPATH = os.path.join(here, 'default-logging.yaml')
LOGGER_NAME = 'cnxarchive'

logger = logging.getLogger(LOGGER_NAME)


class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True
