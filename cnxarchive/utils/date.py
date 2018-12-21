# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2018, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Date/time utility wrappers."""
import datetime
import tzlocal


__all__ = (
    'fromtimestamp',
    'rfc822',
)


def fromtimestamp(ts):
    """Convert a timestamp to a datetime using local timezone."""
    return datetime.datetime.fromtimestamp(ts, tz=tzlocal.get_localzone())


def rfc822(dt):
    """Converts a datatime object to string formatted according to RFC 822."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
