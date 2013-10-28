.. Copyright (c) 2013, Rice University
   This software is subject to the provisions of the GNU Affero General
   Public License version 3 (AGPLv3).
   See LICENCE.txt for details.

Search
======

The ``.sql`` files found in this directory make up the search query.
Files that end with ``.part.sql`` are keyword specific select statements
that are used to make the larger query.

The ``query.sql`` file is the outter most layer of the query.
All the sub queries are used inside of it and unioned.

The query itself is represented in a multi-dictionary format.
For example, the query string ``organic chemistry author:'bill nye'``
would look something like::

    [('text', 'organic'), ('text', 'chemistry'),
     ('author', 'bill nye')]

The query is broken up into key value pairs that can then be used
to make more specific SQL statements.

The keywords can be broken up into four possible categories:

- Search the given value against everything.
- Search the given value against a specific field (or column) by keyword.
- Filter by a limited set value (i.e. by book).
- Order or sort by a given value (i.e. by publication date).

The ``text`` keyword is used against all keyword fields.
It could just as easily be thought of as the wildcard field.

The list of keyword specific search fields is as follows:

:parentAuthor: Search for derived works by an author. Value must be a UUID.
:language: Search for content by language. Value must be a language code.
:subject: Search for subject text. Value can be text.
:fulltext: Search the full document for the given text. Value can be text.
:abstract: Search the abstract for the given text. Value can be text.
:keyword: Search the keywords (or tags) for the given text. Value can be text.
:author: Search for works by author. Value can be text, email or UUID.
:editor: Search for works by editor. Value can be text, email or UUID.
:translator: Search for works by translator. Value can be text, email or UUID.
:maintainer: Search for works by maintainer. Value can be text, email or UUID.
:licensor: Search for works by licensor. Value can be text, email or UUID.
:exact_title: Search the document title for an exact match of the given text.
:title: Search the document title for terms matching the given text.

Filters are keywords as well,
except that they only support a limited set of values.
There are currently three search filters: ``type``, ``pubYear`` and ``authorID``.
The type filter is used to further filter keyword searches.
The possible values for the type field are ``book`` and ``page``.
It is assumed that if the type field is absent, all types are viable.

The last type of keyword search is to order or sort the results
by a specific field.
The ``sort`` keyword accepts a limited set of values by which it will
sort the result in descending order.

Here is an example that would bring this all together.
The query from the web looks something like::

    "nuclear physics" author:'Bill Nye' type:book sort:pubDate

This nicely breaks down into the following data structure (in Python)::

    [('text', 'nuclear physics'),
     ('author', 'Bill Nye'),
     ('type', 'book'),
     ('sort', 'pubDate'),
     ]

The results (in JSON) of this search will look something like::

    {query: {
       limits: [
         {text: "nuclear physics"},
         {author: "Bill Nye"},
         {type: 'book'},
       ],
       sort: ['pubDate'],
     },  // end of query
     results: {
       total: 20,
       items: [
         {id: "bdf58c1d-c738-478b-aea3-0c00df8f617c",
          type: "book",  // in direct relation to mediaType
          title: "Nuclear Physics: The basics and then some",
          // Not the request author.
          authors: ["19819e87-8b51-43e5-a56f-3baffc5ff3bb"],
          keywords: ["characterization", "chemistry"],
          summarySnippet: "NUPH 300 <em>Science University</em>",
          bodySnippet:"... Methods of <strong>nuclear physics</strong> are important ...",
          pubDate:"2013-08-13T12:12Z"
         },
         {id: "bf8c0d8f-1255-47eb-9f17-83705ae4b16f",
          type: "book",
          title: "Nuclear Fission at Work",
          author: ["340e5eed-e923-45b9-99d4-d6f49a55ffb1",
                   "14b70e33-20ce-4dcd-a9b7-1cf36a721a08",
                   "b9e93d15-719a-4595-b923-af00eff1e243"],
          keywords: ["Alternative fuels", "Clean energy", "Nuclear", "Physics",],
          summarySnippet: "This case ..., though not required.",
          // Older publication date...
          pubDate: "2012-08-13T12:12Z"
         },
         { ... <another-document> ...}
       ], // end of items
       // 'limits' is still inside results. Includes limits from query, which have count = total
       limits: [
         // No structure so you you can perform set operations easily with the query limits
         // matches total, because of the type specification.
         {type: "book", count:20},

         // Not suggesting structure, adding space just for visibility
         {author: {"id": "340e5eed-e923-45b9-99d4-d6f49a55ffb1",
                   "website": null,
                   "surname": null,
                   "suffix": null,
                   "firstname": "OpenStax College",
                   "title": null,
                   "othername": null,
                   "email": "info@openstaxcollege.org",
                   "fullname": "OpenStax College"
                  },
          count: 1
         },
         {author: {"id": "14b70e33-20ce-4dcd-a9b7-1cf36a721a08",
                   "website": null,
                   "surname": "Last",
                   "suffix": null,
                   "firstname": "First",
                   "title": null,
                   "othername": null,
                   "email": "first@last.com",
                   "fullname": "First Last"
                  },
          count: 3
         },
         {author: {"id": "b9e93d15-719a-4595-b923-af00eff1e243",
                   "website": null,
                   "surname": "Physics",
                   "suffix": null,
                   "firstname": "College",
                   "title": null,
                   "email": "info@openstaxcollege.org",
                   "fullname": "OSC Physics Maintainer"
                  },
          count: 2
         },
         ...

         {pubYear: 2013, count: 1},
         {pubYear: 2012, count: 4},
         ...

         {keyword: "chemistry", count: 2},
         ...

         {subject: "Science and Technology", count: 19}
         ...
       ]  // end of limits
     } // end of results
    } // end of response
