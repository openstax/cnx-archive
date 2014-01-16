# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from datetime import datetime
import time
import unittest

from .. import sitemap
from . import *


class SitemapTestCase(unittest.TestCase):


    def test_empty_sitemap(self):
        """instantiate sitemap"""
        sm = sitemap.Sitemap()
        self.assertEqual(repr(sm),'<Sitemap (0 entrie(s))>')
        
    def test_empty_sitemap_string(self):
        """instantiate sitemap and make sure it renders"""
        sm = sitemap.Sitemap()
        self.assertEqual(str(sm),'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>\n')
        
    def test_empty_urlEntry(self):
        """test location required"""
        with self.assertRaises(ValueError):
            sitemap.UrlEntry()
        
    def test_simple_urlEntry(self):
        """test w/ location"""
        ue = sitemap.UrlEntry(loc='http://example.com')
        self.assertEqual(repr(ue),"<UrlEntry 'http://example.com'>")
        self.assertEqual(str(ue),'<url>\n<loc>http://example.com</loc>\n</url>\n')
        
    def test_loc_last_urlEntry(self):
        """test w/ location and lastmod (datetime instance)"""
        ue = sitemap.UrlEntry(loc='http://example.com', lastmod = datetime(2013, 10, 20))
        self.assertEqual(repr(ue),"<UrlEntry 'http://example.com'>")
        self.assertEqual(str(ue),'<url>\n<loc>http://example.com</loc>\n<lastmod>2013-10-20T00:00:00</lastmod>\n</url>\n')
        
    def test_loc_last_urlEntry(self):
        """test w/ location and lastmod (string)"""
        ue = sitemap.UrlEntry(loc='http://example.com', lastmod = '2014-22-40T70:00:00Z')
        self.assertEqual(repr(ue),"<UrlEntry 'http://example.com'>")
        self.assertEqual(str(ue),'<url>\n<loc>http://example.com</loc>\n<lastmod>2014-22-40T70:00:00Z</lastmod>\n</url>\n')

    def test_invalid_updatefreq_urlEntry(self):
        """test w/ location and lastmod (datetime instance)"""
        with self.assertRaises(ValueError):
            sitemap.UrlEntry(loc='http://example.com', changefreq='sometime')

    def test_updatefreq_urlEntry(self):
        """test valid changefreq"""
        ue = sitemap.UrlEntry(loc='http://example.com', changefreq='weekly')
        self.assertEqual(repr(ue),"<UrlEntry 'http://example.com'>")
        self.assertEqual(str(ue),'<url>\n<loc>http://example.com</loc>\n<changefreq>weekly</changefreq>\n</url>\n')

    def test_all_urlEntry(self):
        """test w/ loc, changefreq, and lastmod"""
        
        ue = sitemap.UrlEntry(loc='http://example.com', changefreq='weekly', lastmod = datetime(2013, 10, 20))
        self.assertEqual(repr(ue),"<UrlEntry 'http://example.com'>")
        self.assertEqual(str(ue),'<url>\n<loc>http://example.com</loc>\n<lastmod>2013-10-20T00:00:00</lastmod>\n<changefreq>weekly</changefreq>\n</url>\n'
)

    def test_sitemap_invalid_add_url(self):
        """test bad add_url"""
        sm = sitemap.Sitemap()
        with self.assertRaises(ValueError):
            sm.add_url()
        
    def test_sitemap_url(self):
        """build a sitemap with url added as UrlEntry"""
        sm = sitemap.Sitemap()
        ue = sitemap.UrlEntry(loc='http://example.com', changefreq='weekly', lastmod = datetime(2013, 10, 20))
        sm.add_url(ue)
        self.assertEqual(repr(sm),'<Sitemap (1 entrie(s))>')
        self.assertEqual(str(sm),'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url>\n  <loc>http://example.com</loc>\n  <lastmod>2013-10-20T00:00:00</lastmod>\n  <changefreq>weekly</changefreq>\n  </url>\n</urlset>\n')

    def test_sitemap_url_keywords(self):
        """build a sitemap with url added as keywords"""
        sm = sitemap.Sitemap()
        sm.add_url(loc='http://example.com', changefreq='weekly', lastmod = datetime(2013, 10, 20))
        self.assertEqual(repr(sm),'<Sitemap (1 entrie(s))>')
        self.assertEqual(str(sm),'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url>\n  <loc>http://example.com</loc>\n  <lastmod>2013-10-20T00:00:00</lastmod>\n  <changefreq>weekly</changefreq>\n  </url>\n</urlset>\n')

    def test_sitemap_urls(self):
        """build a sitemap with 2 urls"""
        sm = sitemap.Sitemap()
        ue = sitemap.UrlEntry(loc='http://example.com', changefreq='never', lastmod = datetime(2014, 10, 20))
        sm.add_url(ue)
        sm.add_url(loc='http://example.com', changefreq='weekly', lastmod = datetime(2013, 10, 20))
        self.assertEqual(repr(sm),'<Sitemap (2 entrie(s))>')
        self.assertEqual(str(sm),'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url>\n  <loc>http://example.com</loc>\n  <lastmod>2014-10-20T00:00:00</lastmod>\n  <changefreq>never</changefreq>\n  </url>\n  <url>\n  <loc>http://example.com</loc>\n  <lastmod>2013-10-20T00:00:00</lastmod>\n  <changefreq>weekly</changefreq>\n  </url>\n</urlset>\n')
