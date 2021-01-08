#############################
Connexions Archive Repository
#############################

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

To run cnx-archive locally using docker, first install `Docker <https://www.docker.com/community-edition>`_ and then::

    docker-compose build
    docker-compose up

Running the tests can be achived with the following command::

    docker-compose exec archive python setup.py test

Install the PostgreSQL database
--------------------------------

This will require a ``PostgreSQL`` install
that is greater than or equal to version **9.3**,
Note that this is likely to increase to 9.5 soon, for better json support.
We have two postgres extension dependencies:
``plpythonu`` and ``plxslt``.

Mac
===

Use the `PostgresApp <http://postgresapp.com/>`_ (currently using version 9.4).  See Documentation for installing Command Line Tools.

Verify the install and port by using ``pg_lsclusters``. If the 9.4
cluster is not the first one installed (which it likely is not), note
the port and cluster name. For example, the second cluster installed
will end up by default with port 5433, and a cluster named ``main``.

Set the ``PGCLUSTER`` environment variable to make psql and other
postgresql command line tools connect to the appropriate server. For
the example above, use::

    export PGCLUSTER=9.4/main

Installing the PostgreSQL plxslt extension
==========================================


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

Installing the PostgresSQL session_exec extension
=================================================


This is optional, but required if you choose to install the python packages
into a virtualenv.

::

    git clone https://github.com/okbob/session_exec
    cd session_exec
    make USE_PGXS=1 && make USE_PGXS=1 install

This Postgres Extension is used to activate the virtualenv site-packages on
any successful connection to the database, which then allows for importing
packages that are only installed in the virtualenv.

Set up the database and user
============================

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

**Note:** You may need to create the ``postgres`` user: ``psql -d postgres -c "CREATE USER postgres WITH SUPERUSER;"``
::



    psql -U postgres -d postgres -c "CREATE USER cnxarchive WITH SUPERUSER PASSWORD 'cnxarchive';"
    createdb -U postgres -O cnxarchive cnxarchive

#### Install memcached (optional)


If you want to use memcached, you can install memcached and configure the
memcached servers in development.ini::

    apt-get install memcached

Installing the application
--------------------------

To install the application itself::

    python setup.py install

**Note** Make sure that XCode command line tools is installed by typing in::

    xcode-select --install

This will install the package and a few application specific
scripts. 

Run cnx-db with environment variable

    DB_URL=postgresql://cnxarchive@/cnxarchive cnx-db init
    DB_URL=postgresql://cnxarchive@/cnxarchive cnx-db venv

Confirm the table has been created

    psql cnxarchive

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

You can also start the server using pserve

    pserve development.ini

You can then surf to the address printed out by the above commands.

Linux
-----

On Debian (and Ubuntu), issue the following command to installthe default Debian package (PostgreSQL 9.5)::

    sudo apt-get install postgresql postgresql-server-dev-9.5 postgresql-client postgresql-contrib postgresql-plpython

Verify the install and port by using ``pg_lsclusters``. If the 9.5
cluster is not the first one installed (which it likely is not), note
the port and cluster name. For example, the second cluster installed
will end up by default with port 5433, and a cluster named ``main``.

Set the ``PGCLUSTER`` environment variable to make psql and other
postgresql command line tools connect to the appropriate server. For
the example above, use::

    export PGCLUSTER=9.5/main


Installing the PostgreSQL plxslt extension
==========================================

The ``plxslt`` package can be found on github at
`petere/plxslt <https://github.com/petere/plxslt>`_).
You'll need to build and install this package manually.

On a Debian based system, the installation is as follows::

    apt-get install libxml2-dev libxslt-dev
    git clone https://github.com/petere/plxslt
    cd plxslt
    make && sudo make install
    cd ..

Installing the PostgresSQL session_exec extension
=================================================


This is optional, but required if you choose to install the python packages
into a virtualenv.

::

    git clone https://github.com/okbob/session_exec
    cd session_exec
    make USE_PGXS=1 && sudo make USE_PGXS=1 install

This Postgres Extension is used to activate the virtualenv site-packages on
any successful connection to the database, which then allows for importing
packages that are only installed in the virtualenv.

Set up the database and user
============================

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

::



    psql -U postgres -d postgres -c "CREATE USER cnxarchive WITH SUPERUSER PASSWORD 'cnxarchive';"
    createdb -U postgres -O cnxarchive cnxarchive


Install memcached (optional)
============================


If you want to use memcached, you can install memcached and configure the
memcached servers in development.ini::

    apt-get install memcached

Installing the application
==========================

To install the application itself::

    python setup.py install


This will install the package and a few application specific
scripts. 

Run cnx-db with environment variable

    DB_URL=postgresql://cnxarchive@/cnxarchive cnx-db init
    DB_URL=postgresql://cnxarchive@/cnxarchive cnx-db venv

Confirm the table has been created

    psql cnxarchive

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

You can also start the server using pserve

    pserve development.ini

You can then surf to the address printed out by the above commands.

Running tests
-------------

Create the test database
========================

    createdb -U postgres -O cnxarchive cnxarchive-testing

.. image:: https://img.shields.io/codecov/c/github/Connexions/cnx-archive.svg
   :target: https://codecov.io/gh/Connexions/cnx-archive

The tests use the standard library ``unittest`` package and can therefore
be run with minimal effort. Set the environment variable TESTING_CONFIG to point to your testing configuration file. A default example can be found at ``cnxarchive/tests/testing.ini``, and can be used directly or copied to another location and modified. Please do not modify it in place unless you intend to change the defaults for everyone.::

    export TESTING_CONFIG=testing.ini

Then, use either of the following to invoke the test suite::

    $ python -m unittest discover
    $ python setup.py test

Or with `pytest <https://docs.pytest.org/en/latest/getting-started.html>`_, if you have it installed::

    $ pytest

This uses sample data found in the ``cxarchive/tests/data`` directory.

Usage
-----
 * `Content API <./docs/content_api_doc.md>`_
 * `Search API <./docs/search_api_doc.rst>`_

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2019 Rice University
