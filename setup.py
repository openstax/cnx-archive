# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'PasteDeploy',
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
    """,
    test_suite='cnxarchive.tests'
    )
