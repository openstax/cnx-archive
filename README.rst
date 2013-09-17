Connexions Archive Repository
=============================

This is an archive for Connexions documents. It holds published
documents and collections of documents. It is accessible to the public via
a read-only API. It has an optional write API for publishing content
from an unpublished repository (e.g. ``rhaptos2.repo``).

Getting started
---------------

This will require a 'Postgres' version 9.3 install
and the 'plpythonu' extension.
If you are using the ``development.ini`` configuration file,
you'll want to set up a ``cnxarchive`` database for user ``cnxarchive``
with the password ``cnxarchive``.

Before installing cnx-archive, you need to first install its dependencies::

    $ git clone git@github.com:Connexions/cnx-query-grammar.git
    $ cd cnx-query-grammar
    $ python setup.py install

The application is built in Python and can be installed using the
typical Python distribution installation procedure, as follows::

    $ python setup.py install

This will install the package and a few application specific
scripts. One of these scripts is used to initialize the database with
the applications schema.
::

    $ initialize_cnx-archive_db development.ini

To run the application, use the ``paste`` script with the ``serve`` command.
(The paste script and serve command come from ``PasteScript`` and
``PasteDeploy``, respectively.) This example uses the ``development.ini``,
which has been supplied with the package.
::

    $ paster serve development.ini

You can then surf to the address printed out by the above command.

Running tests
-------------

.. image:: https://travis-ci.org/Connexions/cnx-archive.png?branch=master
   :target: https://travis-ci.org/Connexions/cnx-archive

The tests use the standard library ``unittest`` package and can therefore
be run with minimal effort. Either of the following will work::

    $ python -m unittest discover
    $ python setup.py test

This uses example data found in the test-data directory.

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2013 Rice University
