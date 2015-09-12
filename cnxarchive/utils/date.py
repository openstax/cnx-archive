# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import datetime
import tzlocal


__all__ = ('fromtimestamp',)


def fromtimestamp(ts):
    return datetime.datetime.fromtimestamp(ts, tz=tzlocal.get_localzone())
