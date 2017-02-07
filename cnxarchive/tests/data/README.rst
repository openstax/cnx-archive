:data.sql:
    Generated via::
        cnx-db init -d cnxarchive-testing -U cnxarchive
        pg_dump -a -T schema_migrations -T licenses -T tags -T roles -T modulestates -T service_states --disable-triggers --inserts cnxarchive-testing > cnxarchive/tests/data/data.sql

        If you have a a feature branch with schema and/or data changes, you'll
        need to build a migration. Which is basically a schema-diff. The workflow below
        uses tools from Pyrseas https://github.com/perseas/Pyrseas. It's slightly simplier if
        you can make the migrations steps by hand.
            git checkout myfeature
            cnx-archive-initdb cnxarchive/tests/testing.ini
            # dump a schema
            dbtoyaml cnxarchive-testing -o cnxarchive-myfeature.yml
            dropdb cnxarchive-testing; createdb -O cnxarchive cnxarchive-testing
            git checkout master
            cnx-archive-initdb cnxarchive/tests/testing.ini
            # dump a schema
            dbtoyaml cnxarchive-testing -o cnxarchive-master.yml
            # Initialize the schema manager
            dbmigrator --config cnxarchive/tests/testing.ini init
            # Create the schema migration step
            dbmigrator generate <description of the change>
            # Make needed changes via db-migrator migrations
            yamltodb cnxarchive-testing cnxarchive-myfeature.yml >myfeature-up.sql
            # use the SQL as part of up() method - include data migrations as well
            dbmigrator --config cnxarchive/tests/testing.ini migrate
            # Make needed changes via db-migrator migrations
            yamltodb cnxarchive-testing cnxarchive-archive.yml >myfeature-down.sql
            # use the SQL as part of down()
            git checkout myfeature
            git add <migration-file>
            
