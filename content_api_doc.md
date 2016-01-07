Content API
===========

**Book metadata and Table of Contents as json**

  >GET http://archive.cnx.org/contents/[book UUID].json

Example

  >http://archive.cnx.org/contents/031da8d3-b525-429c-80cf-6c8ed997733a.json

**Page metadata and HML content as json**

  >GET http://archive.cnx.org/contents/[page UUID].json

Example

  >http://archive.cnx.org/contents/e12329e4-8d6c-49cf-aa45-6a05b26ebcba.json

**Page HTML without styling**

  >GET http://archive.cnx.org/contents/[page UUID].html

Example

  >http://archive.cnx.org/contents/e12329e4-8d6c-49cf-aa45-6a05b26ebcba.html

Notes
=====

1. Short IDs do not work for retrieving from archive. The full UUID for a Book and the current Page can be found in the More Information tab at the bottom of any content
2. All CNX content has a version numbers which is displayed as @[version#]. Removing the version will always give you the latest version of the content
