# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'cnx-query-grammar',
    'cnx-epub',
    'lxml',
    'python-memcached',
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
    version='1.2.0',
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
    cnx-archive-initdb = cnxarchive.scripts.initializedb:main
    cnx-archive-initialize_db = cnxarchive.scripts.initializedb:main
    cnx-archive-hits_counter = cnxarchive.scripts.hits_counter:main
    """,
    test_suite='cnxarchive.tests'
    )
