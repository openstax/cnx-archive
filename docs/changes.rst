
.. Use the following to start a new version entry:

   |version|
   ----------------------

   - feature message

3.6.1
-----

- Change order of links in sitemap - newest first (SEO test)

3.6.0
-----

- Fix issue #420 - access to zips for pages
- Add additional human-readable fields to /extras/<id>/books/authors


3.5.0
-----

- Add cache controls on content routes and condense content routes to one
  route declaration (#545)

3.4.0
-----

- Restore a /robots.txt route. Returns do not index robots.txt (#547)

3.3.0
-----

- Change "302 Found" redirects to "301 Permanently Moved"
  for shortid and legacy redirects

3.2.0
-----

- Removed robots.txt generation - handled upstream (#536)

3.1.0
-----

- Add list of books containing the in context page to
  ``/extras/{ident_hash}``. (#502)

3.0.0
-----

- Move transforms to cnxdb.triggers.transforms
- Wait for the archive container to be up in .travis.yml (#539)
- Remove cnx-archive-initdb commandline script
- Fix tests usage of cnxdb initdb to use a sqlalchemy engines
- Add DB_URL and DB_SUPER_URL to the travis docker config

2.8.0
-----

- Python 3 compatability fixes
- Fix crashing with long search queries (#517)
- Implement multi-part sitemap.xml to allow for more content

2.7.0
-----

- Use cnx-db docker image in travis tests (#521)
- update test data and tests for subcol uuids and fulltext-book search (#529)
- Fix update latest trigger tests to use legacy version in inserts
- Install tzdata for cnx-archive docker image
- Update book search test following changes in book search sql
- In book search to provide query_type parameterization for AND vs OR queries (#532)

2.6.1
-----

- Explicitly close all psycopg2 db connections (#528)

2.6.0
-----

- Check number of matches per page for baked page search (#526)
- Use new method to get latest version (#525)
- Add rhaptos.cnxmlutils version to index.cnxml.html (#523)
- Add an XPath search view (#506)
- Fix recent RSS to include all authors and utf-8 names (#516)
- Fix multiple copies of new version after republish (#509)
- Pin webtest to 2.0.27 (#510)
- Fix tree_to_json arg type used in transforms (#503)
- Fix OAI feed templates to remove tal and metal declarations (#500)
- Improve mock plpy api compatability (#496)
- Add the content state to the extras view (#493)
- fix unit test from a schema change in cnx-db (#501)
- Fix plpy testing mock to ensure json data type conversion (#497)
- Reorganizing views into a subpackage (#491)
- Use versioneer for package versioning (#495)
- Add an OAI feed (#489)
- Migrate the testing data (#492)
- Add a recent RSS feed (#488)
- Declare type info on startup rather than at runtime (#486)
- Handle broken legacy redirects with 404 (#477)
- Bump the subcollection minor version on revision publications (#476)
- Fix to include an abstract value because cnx-authoring requires it (#481)
- Fix test results for cnx-epub change
- Fix correctly identify composite-module subcollection using the in database
  serial counters (#480)
- Inhert some metadata from down the tree when building models (#479)
- Shortids in tree (#475)
- Update README to mention Python version and installing
  PasteScript and PasteDeploy (#475)
- Export baked (internal) epub (#473)
- Assign subcollection (chapter) ids (#472)
- Convert SQL to use ident_hash and module_version funcs
  to take advantage of indexes (#470)
- Move all sql schema and query files to cnx-db (#443)
- Fix legacy republish of collection w/ subcollections (#469)
- Remove subcollection metadata data migration
- Fix subcollection metadata migration to point at the sql files
  relative to the migration (#468)
- Create SubCollection metadata objects when shredding collxml (#462)
- Update tests to use latest pyramid, skip DTD dependent tests and
  skip memcached dependent tests when memcached isn't available (#467)
- Encode shortid in export epub metadata (#464)
- Fix revision publication triggers to use raw collection content rather
  than the collated (baked) content (#463)
- Add missing fulltext index function migration (#461)
- Fix collated fulltext indexing triggers (#460)
- Fix in-book search to limit the context to a single baked book (#460)
- Add in-book search for collated (baked) documents (#459)
- Preserve files on collection revision publications (#455)
- Add the as_collated query-string parameter to content views (#453)
- Fix duplicate minor versions created by republish trigger (#451)
- Move modulestates to schema initialization (#450)
- Fix document factory error when resource uri doesn't have a filename (#447)
- Add sql function to remove html tags in title search results (#446)
- Add post-publication states and add a trigger to notify publishing
  to process post publication events (#445)
- Fix  submitter/log on collection republish (#444)

2.5.1
-----

- (unknown?)
