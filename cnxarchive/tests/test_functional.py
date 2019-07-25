# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
try:
    from unittest import mock  # python 3
except ImportError:
    import mock  # python 2
try:
    from urllib.parse import urljoin
except:
    from urlparse import urljoin
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from ..utils import CNXHash
from . import testing


class IdentHashSyntaxErrorTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_get_export_invalid_id(self):
        self.testapp.get('/exports/abcd.pdf', status=404)

    def test_get_extra_invalid_id(self):
        self.testapp.get('/extras/abcd', status=404)

    def test_in_book_search_invalid_id(self):
        self.testapp.get('/search/abcd?q=air+or+liquid+drag',
                         status=404)

    def test_in_book_search_highlighted_results_invalid_id(self):
        self.testapp.get('/search/abcd:efgh?q=air+or+liquid+drag',
                         status=404)

    def test_contents_uuid_only_w_at_sign(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        self.testapp.get('/contents/{}@'.format(uuid), status=404)

    def test_contents_short_id_only_w_at_sign(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        short_id = CNXHash(uuid).get_shortid()
        self.testapp.get('/contents/{}@'.format(short_id), status=404)

    def test_contents_invalid_id_w_at_sign(self):
        self.testapp.get('/contents/a@', status=404)

    def test_contents_w_only_at_sign(self):
        self.testapp.get('/contents/@', status=404)


class IdentHashShortIdTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    contents_extensions = ['', '.json', '.html']

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_contents_shortid_version(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        short_id = CNXHash(uuid).get_shortid()

        for ext in self.contents_extensions:
            resp = self.testapp.get('/contents/{}@8{}'.format(short_id, ext))
            self.assertEqual(resp.status, '301 Moved Permanently')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@8{}'.format(uuid, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_contents_shortid_wo_version(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        short_id = CNXHash(uuid).get_shortid()

        for ext in self.contents_extensions:
            resp = self.testapp.get('/contents/{}{}'.format(short_id, ext))
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@5{}'.format(uuid, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_contents_page_inside_book_version_mismatch_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        for ext in self.contents_extensions:
            resp = self.testapp.get(
                '/contents/{}@{}:{}@0{}'.format(
                    book_shortid, book_version, page_shortid, ext))
            self.assertEqual(resp.status, '301 Moved Permanently')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}:{}@0{}'.format(
                    book_uuid, book_version, page_shortid, ext))

            self.testapp.get(resp.location, status=404)

    def test_contents_page_inside_book_w_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        for ext in self.contents_extensions:
            resp = self.testapp.get('/contents/{}@{}:{}@{}{}'.format(
                book_shortid, book_version, page_shortid, page_version, ext))
            self.assertEqual(resp.status, '301 Moved Permanently')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}:{}@{}{}'.format(
                    book_uuid, book_version, page_shortid, page_version, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}{}'.format(
                    page_uuid, page_version, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_contents_page_inside_book_wo_version_shortid(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'
        book_shortid = CNXHash(book_uuid).get_shortid()
        page_shortid = CNXHash(page_uuid).get_shortid()

        for ext in self.contents_extensions:
            resp = self.testapp.get('/contents/{}:{}{}'.format(
                book_shortid, page_shortid, ext))
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}:{}{}'.format(
                    book_uuid, book_version, page_shortid, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}{}'.format(
                    page_uuid, page_version, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_contents_not_found_w_invalid_uuid(self):
        for ext in self.contents_extensions:
            self.testapp.get('/contents/notfound@1{}'.format(ext), status=404)

    def test_extras_shortid_w_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        short_id = CNXHash(uuid).get_shortid()
        version = '7.1'

        resp = self.testapp.get('/extras/{}@{}'.format(short_id, version))
        self.assertEqual(resp.status, '301 Moved Permanently')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/extras/{}@{}'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_extras_shortid_wo_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        short_id = CNXHash(uuid).get_shortid()
        version = '7.1'

        resp = self.testapp.get('/extras/{}'.format(short_id))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/extras/{}@{}'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_in_book_shortid_w_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        short_id = CNXHash(uuid).get_shortid()
        version = '7.1'

        resp = self.testapp.get('/search/{}@{}?q=air'.format(
            short_id, version))
        self.assertEqual(resp.status, '301 Moved Permanently')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}?q=air'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_in_book_shortid_wo_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        short_id = CNXHash(uuid).get_shortid()
        version = '7.1'

        resp = self.testapp.get('/search/{}?q=air'.format(short_id))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}?q=air'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_page_in_book_w_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_short_id = CNXHash(book_uuid).get_shortid()
        book_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_short_id = CNXHash(page_uuid).get_shortid()
        page_version = '8'

        resp = self.testapp.get('/search/{}:{}?q=air'.format(
            book_short_id, page_short_id))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}:{}?q=air'.format(
                book_uuid, book_version, page_short_id))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_page_in_book_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_short_id = CNXHash(book_uuid).get_shortid()
        book_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_short_id = CNXHash(page_uuid).get_shortid()
        page_version = '8'

        resp = self.testapp.get('/search/{}@{}:{}?q=air'.format(
            book_short_id, book_version, page_short_id))
        self.assertEqual(resp.status, '301 Moved Permanently')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}:{}?q=air'.format(
                book_uuid, book_version, page_short_id))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')


class IdentHashMissingVersionTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    contents_extensions = ['', '.json', '.html']

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_contents_uuid_not_found(self):
        uuid = '98c44aed-056b-450a-81b0-61af87ee75af'

        for ext in self.contents_extensions:
            self.testapp.get('/contents/{}{}'.format(uuid, ext), status=404)

    def test_contents_page_inside_book_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = 'f3c9ab70-a916-4d8c-9256-42953287b4e9'
        page_version = '3'

        for ext in self.contents_extensions:
            resp = self.testapp.get('/contents/{}:{}{}'.format(
                book_uuid, page_uuid, ext))
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}:{}{}'.format(
                    book_uuid, book_version, page_uuid, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '302 Found')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@{}{}'.format(
                    page_uuid, page_version, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_exports_wo_version(self):
        uuid = 'c0a76659-c311-405f-9a99-15c71af39325'
        version = 5

        resp = self.testapp.get('/exports/{}.zip'.format(uuid))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/exports/{}@{}.zip'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_exports_wo_version_not_found(self):
        uuid = 'ae3e18de-638d-4738-b804-dc69cd4db3a3'
        version = 5

        resp = self.testapp.get('/exports/{}.zip'.format(uuid))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/exports/{}@{}.zip'.format(uuid, version))

        resp.follow(status=404)

    def test_extras_wo_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        resp = self.testapp.get('/extras/{}'.format(uuid))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/extras/{}@{}'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_in_book_wo_version(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        version = '7.1'

        resp = self.testapp.get('/search/{}?q=air'.format(uuid))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}?q=air'.format(uuid, version))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')

    def test_search_page_in_book_wo_version(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        page_version = '8'

        resp = self.testapp.get('/search/{}:{}?q=air'.format(
            book_uuid, page_uuid))
        self.assertEqual(resp.status, '302 Found')
        self.assertEqual(
            unquote(resp.location),
            'http://localhost/search/{}@{}:{}?q=air'.format(
                book_uuid, book_version, page_uuid))

        resp = resp.follow()
        self.assertEqual(resp.status, '200 OK')


class SlugTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    contents_extensions = ['', '.json', '.html']

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_contents_uuid_version_slug(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        slug = 'test-slug'

        for ext in self.contents_extensions:
            resp = self.testapp.get(
                '/contents/{}@8/{}{}'.format(uuid, slug, ext))
            self.assertEqual(resp.status, '200 OK')

    def test_contents_shortid_version_slug(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        short_id = CNXHash(uuid).get_shortid()
        slug = 'TëSt_SlÜg'

        for ext in self.contents_extensions:
            resp = self.testapp.get(
                '/contents/{}@8/{}{}'.format(short_id, slug, ext))
            self.assertEqual(resp.status, '301 Moved Permanently')
            self.assertEqual(
                unquote(resp.location),
                'http://localhost/contents/{}@8/{}{}'.format(uuid, slug, ext))

            resp = resp.follow()
            self.assertEqual(resp.status, '200 OK')

    def test_contents_uuid_version_invalid_slug(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        slug = 'test/slug'

        for ext in self.contents_extensions:
            self.testapp.get('/contents/{}@8/{}{}'.format(uuid, slug, ext),
                             status=404)

    def test_contents_shortid_version_invalid_slug(self):
        uuid = '56f1c5c1-4014-450d-a477-2121e276beca'
        short_id = CNXHash(uuid).get_shortid()
        slug = 'file.png'

        for ext in self.contents_extensions:
            self.testapp.get('/contents/{}@8/{}{}'.format(short_id, slug, ext),
                             status=404)


class XPathTestCase(testing.FunctionalTestCase):
    fixture = testing.data_fixture

    def setUp(self):
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_xpath_utf8(self):
        resp = self.testapp.get(
            '/xpath.json?id=kctfKCuK@1&q=//h:p[@id="para1"]&type=html')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.json[0]["title"], u"Indkøb")

        resp = self.testapp.get(
            '/xpath.html?id=kctfKCuK@1&q=//h:p[@id="para1"]&type=html')
        self.assertEqual(resp.status, '200 OK')
        self.assertIn(
            '<a href="/contents/91cb5f28-2b8a-4324-9373-dac1d617bc24@1">'
            'Indkøb</a>',
            resp.body)
