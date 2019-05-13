# -*- coding: utf-8 -*-
import os
import versioneer
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def _filter_requirement(req):
    req = req.strip()
    # skip comments and dash options (e.g. `-e` & `-r`)
    return bool(req and req[0] not in '#-')


def read_from_requirements_txt(filepath):
    f = os.path.join(here, filepath)
    with open(f) as fb:
        return tuple([
            x.strip()
            for x in fb
            if _filter_requirement(x)
        ])


install_requires = read_from_requirements_txt('requirements/main.txt')
tests_require = read_from_requirements_txt('requirements/test.txt')
extras_require = {
    'test': tests_require,
}
description = "An archive for Connexions documents."


setup(
    name='cnx-archive',
    version=versioneer.get_version(),
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
        'cnxarchive': ['sql/*.sql', 'sql/*/*.sql', 'data/*.*', '*.yaml',
                       'views/templates/*.*'],
        'cnxarchive.tests': ['data/*.*'],
        },
    cmdclass=versioneer.get_cmdclass(),
    entry_points="""\
    [paste.app_factory]
    main = cnxarchive:main
    [console_scripts]
    cnx-archive-hits_counter = cnxarchive.scripts.hits_counter:main
    cnx-archive-inject_resource = cnxarchive.scripts.inject_resource:main
    cnx-archive-export_epub = cnxarchive.scripts.export_epub.main:main
    [dbmigrator]
    migrations_directory = cnxarchive:find_migrations_directory
    """,
    test_suite='cnxarchive.tests'
    )
