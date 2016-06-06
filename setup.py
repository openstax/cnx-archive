# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages

IS_PY3 = sys.version_info > (3,)

install_requires = (
    'cnx-query-grammar',
    'cnx-epub',
    'lxml',
    'python-memcached',
    'psycopg2>=2.5',
    'pyramid',
    'rhaptos.cnxmlutils',
    'tzlocal',
    'waitress',  # wsgi server
    )
tests_require = [
    'webtest'
    ]
description = "An archive for Connexions documents."

if not IS_PY3:
    tests_require.append('mock==1.0.1')

setup(
    name='cnx-archive',
    version='2.5.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-archive",
    license='LGPL, See also LICENSE.txt',
    description=description,
    packages=find_packages(),
    install_requires=install_requires,
    tests_require=tests_require,
    include_package_data=True,
    package_data={
        'cnxarchive': ['sql/*.sql', 'sql/*/*.sql', 'data/*.*', '*.yaml'],
        'cnxarchive.tests': ['data/*.*'],
        },
    entry_points="""\
    [paste.app_factory]
    main = cnxarchive:main
    [console_scripts]
    cnx-archive-initdb = cnxarchive.scripts.initializedb:main
    cnx-archive-hits_counter = cnxarchive.scripts.hits_counter:main
    cnx-archive-inject_resource = cnxarchive.scripts.inject_resource:main
    cnx-archive-export_epub = cnxarchive.scripts.export_epub.main:main
    [dbmigrator]
    migrations_directory = cnxarchive:find_migrations_directory
    """,
    test_suite='cnxarchive.tests'
    )
