Connexions Archive Repository
=============================

This is an archive for Connexions documents. It holds published
documents and collections of documents. It is accessible to the public via
a read-only API. It has an optional write API for publishing content
from an unpublished repository (e.g. ``rhaptos2.repo``).

Getting started
---------------

This installation procedure attempts to cover two platforms,
the Mac and Debian based systems.
If you are using a platform other these,
attempt to muddle through the instructions,
then feel free to either file an
`issue <https://github.com/Connexions/cnx-archive/issues/new>`_
or contact Connexions for further assistance.

Install the Postgres database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This will require a 'Postgres' install
that is greater than or equal to version 9.3.
We have two postgres extension dependencies:
``plpythonu`` and ``plxslt``.

On a Mac, use the `PostgresApp <http://postgresapp.com/>`_.

On Debian (and Ubuntu), issue the following command::

    apt-get install postgresql-9.3 postgresql-server-dev-9.3 postgresql-client-9.3 postgresql-contrib-9.3 postgresql-plpython-9.3

Installing the Postgres plpythonu extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``plpythonu`` extension comes with the `PostgresApp`,
which you don't have to install this one manuallly.
And we've included the ``postgresql-plpython`` package
in the previous installation command.

Installing the Postgres plxslt extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``plxslt`` package can be found on github at
`petere/plxslt <https://github.com/petere/plxslt>`_).
You'll need to build and install this package manually.

On a Mac, this can be done using the following commands,
assuming you have both `PostgresApp` and
`homebrew <http://brew.sh/>`_ installed.

::

    brew install libxml2 libxslt
    git clone https://github.com/petere/plxslt
    cd plxslt
    export PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig:/usr/local/opt/libxslt/lib/pkgconfig
    make && make install

On a Debian based system, the installation is as follows::

    apt-get install libxml2-dev libxslt-dev
    git clone https://github.com/petere/plxslt
    cd plxslt
    make && make install

Set up the database and user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default settings
for the database are setup to use the following credentials:

:database-name: cnxarchive
:database-user: cnxarchive
:database-password: cnxarchive

.. note:: Not that it needs to be said, but just in case...
   In a production setting, you should change these values.

If you decided to change any of these default values,
please ensure you also change them in the application's configuration file,
which is discussed later in this instructions.

To set up the database, issue the following commands::

    psql -d postgres -c "CREATE USER cnxarchive WITH SUPERUSER PASSWORD 'cnxarchive';"
    createdb -O cnxarchive cnxarchive

Installing the application
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Note**: cnx-archive requires the packages in this section to be installed
with the system python.  Specifically it needs to be installed to the python
that postgresql uses for python triggers.

Before installing cnx-archive, you need to first install the
dependencies that have not been released to the public package repositories::

    git clone https://github.com/Connexions/cnx-query-grammar.git
    cd cnx-query-grammar
    python setup.py install
    cd ..
    git clone https://github.com/Connexions/cnx-upgrade.git
    cd cnx-upgrade
    python setup.py install
    cd ..
    git clone -b abstracts-and-metadata https://github.com/Connexions/rhaptos.cnxmlutils.git
    cd rhaptos.cnxmlutils
    python setup.py install
    cd ..

To install the application itself::

    python setup.py install

This will install the package and a few application specific
scripts. One of these scripts is used to initialize the database with
the applications schema.
::

    initialize_cnx-archive_db development.ini

You can optionally pass ``--with-example-data``
to the database initialization command,
which will populate the database with a small set of content.

To run the application, use the ``paste`` script with the ``serve`` command.
(The paste script and serve command come from ``PasteScript`` and
``PasteDeploy``, respectively.)
This example uses the ``development.ini``,
which has been supplied with the package.
If you changed any of the database setup values,
you'll also need to change them in the configuration file.
::

    paster serve development.ini

You can then surf to the address printed out by the above command.

Running tests
-------------

.. image:: https://travis-ci.org/Connexions/cnx-archive.png?branch=master
   :target: https://travis-ci.org/Connexions/cnx-archive

The tests use the standard library ``unittest`` package and can therefore
be run with minimal effort. Make a testing config, such as testing.ini,
and set the environment variable ``TESTING_CONFIG`` to the name of that file::

    export TESTING_CONFIG=testing.ini

Then, either of the following will work::

    $ python -m unittest discover
    $ python setup.py test

This uses example data found in the test-data directory.

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2013 Rice University
