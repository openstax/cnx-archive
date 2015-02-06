# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Backward compatible module... moved to transforms.py

Upgrades for munging/transforming Connexions XML formats to HTML.

"""
# BBB 17-Dec-2014 moved - Moved function to the transforms module.
#     Remove when references from cnx-upgrade have been fixed or removed.
from .transforms import (
    MODULE_REFERENCE, RESOURCE_REFERENCE,
    transform_cnxml_to_html,
    produce_html_for_module, produce_html_for_abstract,
    ##transform_abstract, transform_module_content,
    fix_reference_urls, parse_reference,
    ReferenceResolver,
    IndexHtmlExistsError, MissingDocumentOrSource, MissingAbstract,
    ReferenceNotFound,
    )
