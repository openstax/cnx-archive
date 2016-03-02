# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###


class NotFound(Exception):
    """Raised when identified content cannot be found in the database."""


class ContentNotFound(Exception):
    """Raised when file content's of the identified content cannot be found
    in the database.

    """


class FileNotFound(Exception):
    """Raised when a file cannot be found."""


__all__ = (
    'ContentNotFound',
    'FileNotFound',
    'NotFound',
    )
