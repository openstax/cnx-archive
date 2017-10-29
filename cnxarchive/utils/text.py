# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2015, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Text manipulation methods."""
import re
import unicodedata


__all__ = ('slugify', 'utf8',)


def slugify(string):
    """Return a slug for the unicode_string.

    (lowercase, only letters and numbers, hyphens replace spaces)
    """
    filtered_string = []
    if isinstance(string, str):
        string = unicode(string, 'utf-8')
    for i in unicodedata.normalize('NFKC', string):
        cat = unicodedata.category(i)[0]
        # filter out all the non letter and non number characters from the
        # input (L is letter and N is number)
        if cat in 'LN' or i in '-_':
            filtered_string.append(i)
        elif cat in 'Z':
            filtered_string.append(' ')
    return re.sub('\s+', '-', ''.join(filtered_string)).lower()


def utf8(item):
    """Change all python2 str/bytes instances to unicode/python3 str."""
    if isinstance(item, list):
        return [utf8(i) for i in item]
    if isinstance(item, tuple):
        return tuple([utf8(i) for i in item])
    if isinstance(item, dict):
        return {utf8(k): utf8(v) for k, v in item.items()}
    try:
        return item.decode('utf-8')
    except:  # bare except since this method is supposed to be safe anywhere
        return item
