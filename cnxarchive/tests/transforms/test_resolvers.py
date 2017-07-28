# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import io
import unittest

from lxml import etree
from pyramid import testing as pyramid_testing

from .. import testing


class HtmlReferenceResolutionTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    def setUp(self):
        settings = testing.integration_test_settings()
        config = pyramid_testing.setUp(settings=settings)
        self.fixture.setUp()

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    @property
    def target(self):
        from ...transforms.resolvers import resolve_cnxml_urls
        return resolve_cnxml_urls

    @testing.db_connect
    def test_reference_rewrites(self, cursor):
        # Case to test that a document's internal references have
        #   been rewritten to the cnx-archive's read-only API routes.
        ident = 3
        from ...transforms.converters import cnxml_to_full_html
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm42119-1.3-modified.cnxml')
        with open(content_filepath, 'r') as fb:
            content = cnxml_to_full_html(fb.read())
            content = io.BytesIO(content)
            content, bad_refs = self.target(content, testing.fake_plpy, ident)

        # Read the content for the reference changes.
        expected_img_ref = '<img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" data-media-type="image/jpg" alt="The spiral galaxy Andromeda is shown."/>'
        self.assertIn(expected_img_ref, content)
        expected_internal_ref = '<a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7">'
        self.assertIn(expected_internal_ref, content)
        expected_resource_ref = '<a href="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg">'
        self.assertIn(expected_resource_ref, content)

    @testing.db_connect
    def test_reference_not_parseable(self, cursor):
        ident = 3
        from ...transforms.converters import cnxml_to_full_html
        import glob
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm45070.cnxml')
        with open(content_filepath, 'r') as fb:
            content = cnxml_to_full_html(fb.read())
        content = io.BytesIO(content)
        content, bad_refs = self.target(content, testing.fake_plpy, ident)

        self.assertEqual(sorted(bad_refs), [
            "Invalid reference value: document=3, reference=/m",
            "Missing resource with filename 'InquiryQuestions.svg', moduleid None version None.: document=3, reference=InquiryQuestions.svg",
            "Unable to find a reference to 'm43540' at version 'None'.: document=3, reference=/m43540",
            ])
        self.assertIn('<a href="/m">', content)

    @testing.db_connect
    def test_reference_resolver(self, cursor):
        html = io.BytesIO('''\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/m42092#xn">
            <img src="Figure_01_00_01.jpg"/>
        </a>
        <a href="/ m42709@1.4">
            <img src="/Figure_01_00_01.jpg"/>
        </a>
        <a href="/m42092/latest?collection=col11406/latest#figure">
            Module link with collection
        </a>
        <a href="/m42955/latest?collection=col11406/1.6">
            Module link with collection and version
        </a>
        <img src=" Figure_01_00_01.jpg"/>
        <img src="/content/m42092/latest/PhET_Icon.png"/>
        <img src="/content/m42092/1.4/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="Figure_01_00_01.jpg"/>

        <audio src="Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"></audio>

        <video src="Figure_01_00_01.jpg" id="music" mime-type="video/mp4"></video>

        <object width="400" height="400" data="Figure_01_00_01.jpg"></object>

        <object width="400" height="400">
            <embed src="Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>''')

        html, bad_references = self.target(html,
                                           testing.fake_plpy,
                                           document_ident=3)
        cursor.connection.commit()

        self.assertEqual(bad_references, [
            "Missing resource with filename 'PhET_Icon.png', moduleid m42092 version 1.3.: document=3, reference=PhET_Icon.png",
            ])
        self.assertMultiLineEqual(html, '''\
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce#xn">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/ae3e18de-638d-4738-b804-dc69cd4db3a3@4">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597:d395b566-5fe3-4428-bcb2-19016e3aa3ce#figure">
            Module link with collection
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.2:209deb1f-1a46-4369-9e0d-18674cf58a3e">
            Module link with collection and version
        </a>
        <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <audio src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"/>

        <video src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="video/mp4"/>

        <object width="400" height="400" data="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <object width="400" height="400">
            <embed src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>''')

    @testing.db_connect
    def test_get_resource_info(self, cursor):
        from ...transforms.resolvers import (
            CnxmlToHtmlReferenceResolver as ReferenceResolver,
            ReferenceNotFound,
            )

        resolver = ReferenceResolver(io.BytesIO('<html></html>'),
                                     testing.fake_plpy, 3)

        # Test file not found
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png')

        # Test getting a file in module 3
        self.assertEqual(resolver.get_resource_info('Figure_01_00_01.jpg'),
                         {'hash': 'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9', 'id': 6})

        # Test file not found outside of module 3
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png', document_id='m42955')

        # Test getting a file in another module
        self.assertEqual(resolver.get_resource_info('PhET_Icon.png',
                                                    document_id='m42092'),
                         {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c',
                          'id': 23})

        # Test file not found with version
        self.assertRaises(ReferenceNotFound, resolver.get_resource_info,
                          'PhET_Icon.png', document_id='m42092',
                          version='1.3')

        # Test getting a file with version
        self.assertEqual(resolver.get_resource_info('PhET_Icon.png',
                                                    document_id='m42092',
                                                    version='1.4'),
                         {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c',
                          'id': 23})

    def test_parse_reference(self):
        from ...transforms.resolvers import (
            MODULE_REFERENCE, RESOURCE_REFERENCE,
            parse_legacy_reference as parse_reference,
            )

        self.assertEqual(
            parse_reference('/m12345'),
            (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        self.assertEqual(
            parse_reference('/content/m12345'),
            (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        self.assertEqual(
            parse_reference('http://cnx.org/content/m12345'),
            (MODULE_REFERENCE, ('m12345', None, None, None, '')))

        # m10278 "The Advanced CNXML"
        self.assertEqual(
            parse_reference('/m9007'),
            (MODULE_REFERENCE, ('m9007', None, None, None, '')))

        # m11374 "KCL"
        self.assertEqual(
            parse_reference('/m0015#current'),
            (MODULE_REFERENCE, ('m0015', None, None, None, '#current')))

        # m11351 "electron and hole density equations"
        self.assertEqual(
            parse_reference('/m11332#ntypeq'),
            (MODULE_REFERENCE, ('m11332', None, None, None, '#ntypeq')))

        # m19809 "Gavin Bakers entry..."
        self.assertEqual(
            parse_reference('/ m19770'),
            (MODULE_REFERENCE, ('m19770', None, None, None, '')))

        # m16562 "Flat Stanley.pdf"
        self.assertEqual(
            parse_reference(' Flat Stanley.pdf'),
            (RESOURCE_REFERENCE, ('Flat Stanley.pdf', None, None)))

        # m34830 "Auto_fatalities_data.xls"
        self.assertEqual(
            parse_reference('/Auto_fatalities_data.xls'),
            (RESOURCE_REFERENCE, ('Auto_fatalities_data.xls', None, None)))

        # m35999 "version 2.3 of the first module"
        self.assertEqual(
            parse_reference('/m0000@2.3'),
            (MODULE_REFERENCE, ('m0000', '2.3', None, None, '')))

        # m14396 "Adding a Table..."
        # m11837
        # m37415
        # m37430
        # m10885
        self.assertEqual(parse_reference(
            '/content/m19610/latest/eip-edit-new-table.png'),
            (RESOURCE_REFERENCE, ('eip-edit-new-table.png', 'm19610', None)))

        # m45070
        self.assertEqual(parse_reference('/m'), (None, ()))

        # m45136 "legacy format"
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/latest?collection=col11441/latest'),
            (MODULE_REFERENCE, ('m48897', None, 'col11441', None, '')))
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/1.2?collection=col11441/1.10'),
            (MODULE_REFERENCE, ('m48897', '1.2', 'col11441', '1.10', '')))
        self.assertEqual(parse_reference(
            'http://cnx.org/content/m48897/1.2?collection=col11441/1.10'
            '#figure'),
            (MODULE_REFERENCE, ('m48897', '1.2', 'col11441', '1.10',
             '#figure')))

        # legacy.cnx.org links
        self.assertEqual(parse_reference(
            'http://legacy.cnx.org/content/m48897/latest'),
            (None, ()))
        self.assertEqual(parse_reference(
            'http://legacy.cnx.org/content/m48897/latest?collection=col11441/'
            'latest'), (None, ()))

    @testing.db_connect
    def test_get_page_ident_hash(self, cursor):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        cursor.execute('''\
CREATE FUNCTION test_get_page_ident_hash() RETURNS TEXT AS $$
import io

import plpy

from cnxarchive.transforms.resolvers import CnxmlToHtmlReferenceResolver

resolver = CnxmlToHtmlReferenceResolver(io.BytesIO('<html></html>'), plpy, 3)
result = resolver.get_page_ident_hash(%s, %s, %s, %s)
return result[1]
$$ LANGUAGE plpythonu;
SELECT test_get_page_ident_hash();''',
                       (page_uuid, page_version, book_uuid, book_version))
        self.assertEqual(
            cursor.fetchone()[0],
            '{}@{}:{}@{}'.format(
                book_uuid, book_version, page_uuid, page_version))


class CnxmlReferenceResolutionTestCase(unittest.TestCase):
    fixture = testing.data_fixture
    maxDiff = None

    def setUp(self):
        settings = testing.integration_test_settings()
        config = pyramid_testing.setUp(settings=settings)
        self.fixture.setUp()

    def tearDown(self):
        pyramid_testing.tearDown()
        self.fixture.tearDown()

    @property
    def target(self):
        from ...transforms.resolvers import resolve_html_urls
        return resolve_html_urls

    @property
    def target_cls(self):
        from ...transforms.resolvers import HtmlToCnxmlReferenceResolver
        return HtmlToCnxmlReferenceResolver

    def test_parse_reference(self):
        from ...transforms.resolvers import (
            DOCUMENT_REFERENCE, BINDER_REFERENCE,
            RESOURCE_REFERENCE,
            parse_html_reference as parse_reference,
            )

        title = "Something about nothing"
        id = '49f43184-728f-445f-b669-abda618ab8f4'
        ver = '155'
        id2 = 'ab107da9-84bb-4e3c-95e1-30cff398827a'
        ver2 = '5.1'  # used for binder
        sha1 = '0300e7c72015f9bfe30c3cb2d5e8da12a6fbb6f8'

        # Matching legacy
        self.assertEqual(
            parse_reference('http://legacy.cnx.org/content/m48897/latest'),
            (None, ()))
        self.assertEqual(
            parse_reference('http://legacy.cnx.org/content/m48897/latest?collection=col11441/latest'),
            (None, (),))

        # Matching documents
        self.assertEqual(
            parse_reference('/contents/{}'.format(id)),
            (DOCUMENT_REFERENCE, (id, None, '',)))
        self.assertEqual(
            parse_reference('/contents/{}@{}'.format(id, ver)),
            (DOCUMENT_REFERENCE, (id, ver, '',)))
        # With a fragment...
        self.assertEqual(
            parse_reference('/contents/{}/{}'.format(id, title)),
            (DOCUMENT_REFERENCE, (id, None, '/{}'.format(title),)))
        self.assertEqual(
            parse_reference('/contents/{}@{}/{}'.format(id, ver, title)),
            (DOCUMENT_REFERENCE, (id, ver, '/{}'.format(title),)))
        self.assertEqual(
            parse_reference('/contents/{}#current'.format(id)),
            (DOCUMENT_REFERENCE, (id, None, '#current',)))
        self.assertEqual(
            parse_reference('/contents/{}/{}#current'.format(id, title)),
            (DOCUMENT_REFERENCE, (id, None, '/{}#current'.format(title),)))

        # Binder with document
        self.assertEqual(
            parse_reference('/contents/{}@{}:{}@{}'
                            .format(id, ver2, id2, ver)),
            (BINDER_REFERENCE, (id, ver2, '{}@{}'.format(id2, ver), '',)))
        self.assertEqual(
            parse_reference('/contents/{}@{}:{}'.format(id, ver2, id2)),
            (BINDER_REFERENCE, (id, ver2, id2, '',)))
        # With a fragement...
        self.assertEqual(
            parse_reference('/contents/{}@{}:{}/{}'
                            .format(id, ver2, id2, title)),
            (BINDER_REFERENCE, (id, ver2, id2, '/{}'.format(title),)))
        self.assertEqual(
            parse_reference('/contents/{}@{}:{}@{}/{}'
                            .format(id, ver2, id2, ver, title)),
            (BINDER_REFERENCE,
             (id, ver2, '{}@{}'.format(id2, ver), '/{}'.format(title),)))

        # Matching resource
        self.assertEqual(  # ideal url syntax
            parse_reference('../resources/{}'.format(sha1)),
            (RESOURCE_REFERENCE, (sha1, '',)))
        self.assertEqual(  # not ideal, but could happen
            parse_reference('/resources/{}'.format(sha1)),
            (RESOURCE_REFERENCE, (sha1, '',)))
        # With fragments...
        self.assertEqual(
            parse_reference('../resources/{}/{}.pdf'.format(sha1, title)),
            (RESOURCE_REFERENCE, (sha1, '/{}.pdf'.format(title),)))

        # Matching cnx.org
        self.assertEqual(
            parse_reference('http://cnx.org/contents/{}'.format(id)),
            (DOCUMENT_REFERENCE, (id, None, '')))

        # Incomplete UUID
        self.assertEqual(
            parse_reference('/contents/{}'.format(id[:-8])),
            (None, ()))

    @testing.db_connect
    def test_reference_rewrites(self, cursor):
        # Case to test that a document's internal references have
        #   been rewritten to legacy's read-only API routes.
        ident = 3
        from ...transforms.converters import html_to_full_cnxml
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm99999-1.1.html')
        with open(content_filepath, 'r') as fb:
            content = html_to_full_cnxml(fb.read())
            content = io.BytesIO(content)
            content, bad_refs = self.target(content, testing.fake_plpy, ident)

        cnxml_etree = etree.parse(io.BytesIO(content))
        nsmap = cnxml_etree.getroot().nsmap.copy()
        nsmap['c'] = nsmap.pop(None)

        # Ensure the module-id has been set.
        expected_module_id = 'module-id="m42119"'
        self.assertIn(expected_module_id, content)

        # Read the content for the reference changes.
        # Check the links
        expected_ref = '<link document="m41237" version="1.1">'
        self.assertIn(expected_ref, content)
        expected_resource_ref = '<link resource="Figure_01_00_01.jpg">'
        self.assertIn(expected_resource_ref, content)

        # Check the media/image tags...
        expected_img_thumbnail_ref = 'thumbnail="Figure_01_00_01.jpg"'
        self.assertIn(
            expected_img_thumbnail_ref,
            etree.tostring(cnxml_etree.xpath('//*[@id="image-w-thumbnail"]',
                                             namespaces=nsmap)[0]))
        expected_img_src_ref = 'src="Figure_01_00_01.jpg"'
        self.assertIn(
            expected_img_src_ref,
            etree.tostring(cnxml_etree.xpath('//*[@id="image-w-thumbnail"]',
                                             namespaces=nsmap)[0]))

        # Check the media/video & media/audio tags...
        expected_ref = 'src="Figure_01_00_01.jpg"'
        self.assertIn(
            expected_ref,
            etree.tostring(cnxml_etree.xpath(
                '//*[@id="video-n-audio"]/c:video',
                namespaces=nsmap)[0]))
        self.assertIn(
            expected_ref,
            etree.tostring(cnxml_etree.xpath(
                '//*[@id="video-n-audio"]/c:audio',
                namespaces=nsmap)[0]))

        # Check the flash tag.
        expected_ref = 'src="Figure_01_00_01.jpg"'
        self.assertIn(
            expected_ref,
            etree.tostring(cnxml_etree.xpath(
                '//*[@id="object-embed"]/c:flash',
                namespaces=nsmap)[0]))

        # Check the java-applet tag.
        expected_ref = 'src="Figure_01_00_01.jpg"'
        self.assertIn(
            expected_ref,
            etree.tostring(cnxml_etree.xpath(
                '//*[@id="java-applet"]/c:java-applet',
                namespaces=nsmap)[0]))

        # Check bad reference was not transformed.
        expected_ref = '<link>indkoeb.jpg</link>'
        self.assertIn(expected_ref, content)

    @testing.db_connect
    def test_fix_module_id_fails(self, cursor):
        from ...transforms.resolvers import ReferenceNotFound

        content = """\
<document xmlns="http://cnx.rice.edu/cnxml">
<content><para>hi.</para></content>
</document>"""
        # Note, no ident was given.
        resolver = self.target_cls(io.BytesIO(content),
                                   testing.fake_plpy, None)
        problems = resolver.fix_module_id()
        self.assertEqual(len(problems), 1)
        self.assertEqual(type(problems[0]), ReferenceNotFound)

        # Note, an invalid ident was given.
        resolver = self.target_cls(io.BytesIO(content),
                                   testing.fake_plpy, 789321)
        problems = resolver.fix_module_id()
        self.assertEqual(len(problems), 1)
        self.assertEqual(type(problems[0]), ReferenceNotFound)

    @testing.db_connect
    def test_reference_not_parsable(self, cursor):
        ident = 3
        from ...transforms.converters import html_to_full_cnxml
        content_filepath = os.path.join(testing.DATA_DIRECTORY,
                                        'm99999-1.1.html')
        with open(content_filepath, 'r') as fb:
            content = html_to_full_cnxml(fb.read())
        content = io.BytesIO(content)
        content, bad_refs = self.target(content, testing.fake_plpy, ident)

        self.assertEqual(sorted(bad_refs), [
            "Invalid reference value: document=3, reference=/contents/42ae45b/hello-world",
            "Missing resource with hash: 0f3da0de61849a47f77543c383d1ac621b25e6e0: document=3, reference=None",
            "Unable to find a reference to 'c44477a6-1278-433a-ba1e-5a21c8bab191' at version 'None'.: document=3, reference=/contents/c44477a6-1278-433a-ba1e-5a21c8bab191@12",
            ])
        # invalid ref still in the content?
        self.assertIn('<link url="/contents/42ae45b/hello-world">', content)

    @testing.db_connect
    def test_get_resource_filename(self, cursor):
        # XXX
        from ...transforms.resolvers import (
            HtmlToCnxmlReferenceResolver as ReferenceResolver,
            ReferenceNotFound,
            )

        resolver = ReferenceResolver(io.BytesIO('<html></html>'),
                                     testing.fake_plpy, 3)

        # Test file not found
        self.assertRaises(ReferenceNotFound, resolver.get_resource_filename,
                          'PhET_Icon.png')

        # Test getting a file in module 3
        self.assertEqual(
            resolver.get_resource_filename('d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9'),
            'Figure_01_00_01.jpg')

        # Test file not found outside of module 3
        self.assertRaises(ReferenceNotFound,
                          resolver.get_resource_filename,
                          '075500ad9f71890a85fe3f7a4137ac08e2b7907c')

        # Test getting a file in another module
        resolver.document_ident = 4
        self.assertEqual(
            resolver.get_resource_filename('075500ad9f71890a85fe3f7a4137ac08e2b7907c'),
            'PhET_Icon.png')

        # Test getting a file without an ident.
        resolver.document_ident = None
        self.assertEqual(
            resolver.get_resource_filename('075500ad9f71890a85fe3f7a4137ac08e2b7907c'),
            'PhET_Icon.png')
