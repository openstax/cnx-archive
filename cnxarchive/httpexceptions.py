# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""HTTP exceptions"""


class HTTPException(Exception):
    """Base HTTP exception class"""
    status = None
    content_type = 'text/plain'
    message = ''
    headers = None

    def __call__(self, environ, start_response):
        if self.headers is None:
            self.headers = []
        self.headers.append(('Content-type', self.content_type,))
        start_response(self.status, self.headers)
        return [self.message]


class HTTPNotFound(HTTPException):
    """404 Not Found"""
    status = '404 Not Found'
    message = 'Not Found'


class HTTPInternalServerError(HTTPException):
    """500 Internal Server Error"""
    status = '500 Internal Server Error'
    message = 'Internal server error'


class HTTPFound(HTTPException):
    """302 Found"""
    status = '302 Found'

    def __init__(self, location):
        self.headers = [('Location', location,)]
