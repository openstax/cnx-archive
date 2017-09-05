Connexions Archive Repository
=============================

This is an archive for Connexions documents. It holds published
documents and collections of documents and is designed to work together with `webview <https://github.com/Connexions/webview>`_.
It is accessible to the public via a read-only API. It has an optional write API for publishing content
from an unpublished repository. It runs on Python 2.7.

Getting started
---------------

This installation procedure attempts to cover two platforms,
the Mac and Debian based systems.
If you are using a platform other these,
attempt to muddle through the instructions,
then feel free to either file an
`issue <https://github.com/Connexions/cnx-archive/issues/new>`_
or contact Connexions for further assistance.

Install using docker
--------------------

To run cnx-archive locally using docker::

    docker-compose build
    docker-compose up

Install the PostgreSQL database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This will require a ``PostgreSQL`` install
that is greater than or equal to version **9.3**,
Note that this is likely to increase to 9.5 soon, for better json support.
We have two postgres extension dependencies:
``plpythonu`` and ``plxslt``.

On a Mac, use the `PostgresApp <http://postgresapp.com/>`_ (currently using version 9.4).  See Documentation for installing Command Line Tools.

On Debian (and Ubuntu), issue the following command::

    apt-get install postgresql-9.3 postgresql-server-dev-9.3 postgresql-client-9.3 postgresql-contrib-9.3 postgresql-plpython-9.3

Verify the install and port by using ``pg_lsclusters``. If the 9.3
cluster is not the first one installed (which it likely is not), note
the port and cluster name. For example, the second cluster installed
will end up by default with port 5433, and a cluster named ``main``.

Set the ``PGCLUSTER`` environment variable to make psql and other
postgresql command line tools connect to the appropriate server. For
the example above, use::

    export PGCLUSTER=9.3/main

Installing the PostgreSQL plpythonu extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``plpythonu`` extension comes with the `PostgresApp`,
which you don't have to install this one manuallly.
We've included the ``postgresql-plpython`` package
in the previous installation command, for Debian and Ubuntu.

Installing the PostgreSQL plxslt extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``plxslt`` package can be found on github at
`petere/plxslt <https://github.com/petere/plxslt>`_).
You'll need to build and install this package manually.

On a Mac, this can be done using the following commands,
assuming you have both `PostgresApp` and
`homebrew <http://brew.sh/>`_ installed.


Make sure that ``pkg-config`` is properly install by typing ``pkg-config --version``.  If it isn't installed type ``brew install pkg-config`` to install it.
::

    brew install libxml2 libxslt
    which psql # Make sure this returns: /Applications/Postgres93.app/Contents/MacOS/bin/psql
               # Otherwise, you may need to add this path to ~/.profile
    git clone https://github.com/petere/plxslt
    cd plxslt
    export PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig:/usr/local/opt/libxslt/lib/pkgconfig
    make && make install
    cd ..

On a Debian based system, the installation is as follows::

    apt-get install libxml2-dev libxslt-dev
    git clone https://github.com/petere/plxslt
    cd plxslt
    make && make install
    cd ..

Installing the PostgresSQL session_exec extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is optional, but required if you choose to install the python packages
into a virtualenv.

::

    git clone https://github.com/okbob/session_exec
    cd session_exec
    make USE_PGXS=1 && make USE_PGXS=1 install

If you are using PostgreSQL 9.3 rather than >= 9.4, clone `reedstrm/session_exec <https://github.com/reedstrm/session_exec>`_ instead.

This Postgres Extension is used to activate the virtualenv site-packages on
any successful connection to the database, which then allows for importing
packages that are only installed in the virtualenv.

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

To set up the database, issue the following commands (these will use
the default cluster, as defined above)

**OSX Note:** You may need to create the ``postgres`` user: ``psql -d postgres -c "CREATE USER postgres WITH SUPERUSER;"``
::



    psql -U postgres -d postgres -c "CREATE USER cnxarchive WITH SUPERUSER PASSWORD 'cnxarchive';"
    createdb -U postgres -O cnxarchive cnxarchive


Install memcached (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to use memcached, you can install memcached and configure the
memcached servers in development.ini::

    apt-get install memcached

Installing the application
~~~~~~~~~~~~~~~~~~~~~~~~~~

Before installing cnx-archive, you need to first install the
dependencies that have not been released to the public package repositories::

    git clone https://github.com/Connexions/cnx-query-grammar.git
    cd cnx-query-grammar
    python setup.py install
    cd ..

    git clone https://github.com/Connexions/rhaptos.cnxmlutils.git
    cd rhaptos.cnxmlutils
    python setup.py install
    cd ..

To install the application itself::

    python setup.py install

**OSX Note** Make sure that XCode command line tools is installed by typing in::

    xcode-select --install

This will install the package and a few application specific
scripts. One of these scripts is used to initialize the database with
the applications schema.
::

    cnx-db init -d cnxarchive -U cnxarchive
    psql cnxarchive #to confirm the the table has been created.

You can populate the database with a small set of content with the following
command::

    psql -U cnxarchive cnxarchive <cnxarchive/tests/data/data.sql

To run the application, use the ``paste`` script with the ``serve`` command.
(The paste script and serve command come from ``PasteScript`` and
``PasteDeploy``, respectively.)

This example uses the ``development.ini``, which has been supplied with the
package.  If you changed any of the database setup values, you'll also need to
change them in the configuration file.::

    paster serve development.ini

You can then surf to the address printed out by the above command.

Running tests
-------------

.. image:: https://travis-ci.org/Connexions/cnx-archive.png?branch=master
   :target: https://travis-ci.org/Connexions/cnx-archive

.. image:: https://img.shields.io/codecov/c/github/Connexions/cnx-archive.svg
   :target: https://codecov.io/gh/Connexions/cnx-archive

The tests use the standard library ``unittest`` package and can therefore
be run with minimal effort. Make a testing config, such as testing.ini,
and set the environment variable ``TESTING_CONFIG`` to the name of that file::

    export TESTING_CONFIG=testing.ini

Then, use either of the following to invoke the test suite::

    $ python -m unittest discover
    $ python setup.py test

This uses example data found in the ``cxarchive/tests/data`` directory.

Usage
-----
 * `Content API <./docs/content_api_doc.md>`_
 * `Search API <./docs/search_api_doc.rst>`_

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2013 Rice University
