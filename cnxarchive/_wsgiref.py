# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from wsgiref.simple_server import make_server


def main(app, global_conf, **settings):
    host = settings.get('host', 'localhost')
    port = int(settings.get('port', 6543))
    httpd = make_server(host, port, app)
    print("Serving at http://{}:{}".format(host, port))
    return httpd.serve_forever()
