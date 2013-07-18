# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Document and collection archive web application."""


_settings = None

def get_settings():
    """Retrieve the application settings"""
    global _settings
    return _settings
def _set_settings(settings):
    """Assign the application settings."""
    global _settings
    _settings = settings


def main(global_config, **settings):
    """Main WSGI application function."""
    pass
