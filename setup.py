# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'cnx-query-grammar',
    'lxml',
    'PasteDeploy',
    'PasteScript',
    'plpydbapi',
    'psycopg2>=2.5',
    'rhaptos.cnxmlutils',
    'waitress',  # wsgi server
    )
description = "An archive for Connexions documents."


setup(
    name='cnx-archive',
    version='0.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-archive",
    license='LGPL, See also LICENSE.txt',
    description=description,
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True,
    entry_points="""\
    [paste.app_factory]
    main = cnxarchive:main
    [console_scripts]
    initialize_cnx-archive_db = cnxarchive.scripts.initializedb:main
    """,
    test_suite='cnxarchive.tests'
    )
