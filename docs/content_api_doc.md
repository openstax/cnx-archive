Content API
===========

**Understanding CNX URLs**

The CNX URL structure is

`cnx.org/[book_id][@version#]:[page_id][@version #]/[title]`

 * All version numbers are optional. The lack of a version number will always return the latest version.
 * In the browser, a short id is displayed for books and pages. There is also a longer UUID for books and pages. Either id will work in the API. The full UUID for a Book and the current Page can be found in the More Information tab at the bottom of any content.
 * The title should **not** be included in the content API request.

**Book metadata and Table of Contents as json**

  >`GET http://archive.cnx.org/contents/[book_id].json`

Examples (long UUID and short id with version number)

  >http://archive.cnx.org/contents/031da8d3-b525-429c-80cf-6c8ed997733a.json
  >http://archive.cnx.org/contents/Ax2o07Ul@9.4.json

Short ids work as well. The short id is the one displayed in the browser

**Page metadata and HML content as json**

  >`GET http://archive.cnx.org/contents/[page_id].json`

Examples (long UUID and short id with version number)

  >http://archive.cnx.org/contents/e12329e4-8d6c-49cf-aa45-6a05b26ebcba.json
  >http://archive.cnx.org/contents/4SMp5I1s@2.json

**Page HTML without styling**

  >`GET http://archive.cnx.org/contents/[page_id].html`

Examples (long UUID and short id with version number)
NOTE: leaving off ".html" will still result in HTML being returned

  >http://archive.cnx.org/contents/e12329e4-8d6c-49cf-aa45-6a05b26ebcba.html
  >http://archive.cnx.org/contents/4SMp5I1s@2
