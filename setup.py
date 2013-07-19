# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'PasteDeploy',
    'PasteScript',
    'psycopg2',
    )
description = "An archive for Connexions documents."


setup(
    name='cnx-archive',
    version='0.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-archive",
    license='LGPL, See aslo LICENSE.txt',
    description=description,
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True,
    entry_points="""\
    [paste.app_factory]
    main = cnxarchive:main
    [paste.server_runner]
    main = cnxarchive._wsgiref:main
    [console_scripts]
    initialize_cnx-archive_db = cnxarchive.scripts.initializedb:main
    """,
    test_suite='cnxarchive.tests'
    )
