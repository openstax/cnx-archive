Search API
==========

**Method**::
   
   GET http://archive.cnx.org/search?

**Usage**::
   
   q= QUERY [text:TEXT] [author:AUTHOR] [authorID:ID] [submitterID:SUBMITID] [fulltext:FULLTEXT]...
            [title:TITLE] [abstract:ABSTRACT] [subject:SUBJECT] [keyword:KEY] [type:TYPE]...
            [language:LANG] [pubYear:YEAR] [sort:SORT] [editor:EDITOR] [translator:TRANS]...
            [maintainer:MAINTAIN] [licensor:LICENSE]

Brakets denote an optional filter.

**Parameters**

+-------+--------+-----------------------+
| Field | Type   | Description           |
+-------+--------+-----------------------+
| QUERY | String | General search string |
+-------+--------+-----------------------+

**Filters**

+-----------+---------+---------------------------------+
| Field     | Type    | Description                     |
+-----------+---------+---------------------------------+
| TEXT      | String  | Search text fields for content  |
+-----------+---------+---------------------------------+
| AUTHOR    |         | Search by author contact info.  |
+-----------+---------+---------------------------------+
| ID        |         | Search by a specific author ID  |
+-----------+---------+---------------------------------+
| SUBMITID  |         | Search by submission user id    |
+-----------+---------+---------------------------------+
| FULLTEXT  |         | Search the main body of text    |
+-----------+---------+---------------------------------+
| TITLE     |         | Search title strings            |
+-----------+---------+---------------------------------+
| ABSTRACT  |         | Search abstract text            |
+-----------+---------+---------------------------------+
| SUBJECT   |         | Default Value: Any              |
|           |         |                                 |
|           |         | Allowed Values: Arts, Business, |
|           |         | Humanities,                     |
|           |         | "Mathematics and Statistics",   |
|           |         | "Science and Technology",       |
|           |         | "Social Sciences",              |
+-----------+---------+---------------------------------+
| KEY       |         | Search by keyword               |
+-----------+---------+---------------------------------+
| TYPE      |         | Default value: Any              |
|           |         |                                 |
|           |         | Allowed values: book, page      |
+-----------+---------+---------------------------------+
| LANG      |         | Default value: Any              |
|           |         |                                 |
|           |         | Allowed Values: en (English),   |
|           |         | zh (Chinese), es (Spanish),     |
|           |         | ru (Russian), ar (Arabic),      |
|           |         | bn (Bengali), pt (Portuguese)   |
|           |         | id (Bahasa Indonesian),         |
|           |         | fr (French), etc.               |
|           |         | See http://cnx.org/search       |
|           |         | for complete list.              |
+-----------+---------+---------------------------------+
| SORT      |         | Default value: relevance        |
|           |         |                                 |
|           |         | Allowed values: pubDate,        |
|           |         | popularity, version             |
+-----------+---------+---------------------------------+
| YEAR      | Integer | Default value: Any              |
+-----------+---------+---------------------------------+
| *EDITOR   | String  |                                 |
+-----------+---------+---------------------------------+
| *TRANS    | String  |                                 |
+-----------+---------+---------------------------------+
| *MAINTAIN | String  |                                 |
+-----------+---------+---------------------------------+
| *LICENSE  | String  |                                 |
+-----------+---------+---------------------------------+
 
 \* Currently Not Supported

For example:

If::

   QUERY = Physics
   ID = OpenStaxCollege
   SORT = popularity
   
then::

   http://archive.cnx.org/search?q= QUERY [authorID:ID] [sort:SORT]
                                       
                                       =>
   
   http://archive.cnx.org/search?q= Physics authorID:OpenStaxCollege sort:popularity                                    

**Other Examples**::

   http://archive.cnx.org/search?q= Relativity
   
   http://archive.cnx.org/search?q= Relativity authorID:OpenStaxCollege subject:"Science and Technology"
   
   http://archive.cnx.org/search?q= authorID:OpenStaxCollege

**NOTE**

For most browsers::

   http://archive.cnx.org/search?q=subject:%22Mathematics%20and%20Statistics%22

and::
   
   http://archive.cnx.org/search?q=subject:"Mathematics and Statistics"

are equivalent.


**Returned JSON Example**

.. code-block:: json

   {
       "query": {
           "limits": [
               {
                   "tag": "subject",
                   "value": "Mathematics and Statistics"
               },
               {
                   "index": 0,
                   "tag": "authorID",
                   "value": "cnxcap"
               }
           ],
           "page": 1,
           "per_page": 20,
           "sort": []
       },
       "results": {
           "auxiliary": {
               "authors": [
                   {
                       "firstname": "College",
                       "fullname": "OSC Physics Maintainer",
                       "id": "cnxcap",
                       "surname": "Physics",
                       "title": "",
                   },
                   {
                       "firstname": "",
                       "fullname": "OpenStax College",
                       "id": "OpenStaxCollege",
                       "surname": "OpenStax College",
                       "title": "",
                   }
               ],
               "types": [
                   {
                       "id": "application/vnd.org.cnx.collection",
                       "name": "Book"
                   },
                   {
                       "id": "application/vnd.org.cnx.module",
                       "name": "Page"
                   }
               ]
           },
           "items": [
               {
                   "authors": [
                       {
                           "id": "OpenStaxCollege",
                           "index": 1
                       },
                       {
                           "id": "cnxcap",
                           "index": 0
                       }
                   ],
                   "bodySnippet": null,
                   "id": "209deb1f-1a46-4369-9e0d-18674cf58a3e@7",
                   "keywords": [
                       "college physics",
                       "introduction",
                       "physics"
                   ],
                   "mediaType": "application/vnd.org.cnx.module",
                   "pubDate": "2013-07-31T19:07:20Z",
                   "summarySnippet": null,
                   "title": "Preface to College Physics"
               }
           ],
           "limits": [
               {
                   "tag": "pubYear",
                   "values": [
                       {
                           "count": 1,
                           "value": "2013"
                       }
                   ]
               },
               {
                   "tag": "authorID",
                   "values": [
                       {
                           "count": 1,
                           "index": 1,
                           "value": "OpenStaxCollege"
                       },
                       {
                           "count": 1,
                           "index": 0,
                           "value": "cnxcap"
                       }
                   ]
               },
               {
                   "tag": "type",
                   "values": [
                       {
                           "count": 0,
                           "value": "application/vnd.org.cnx.collection"
                       },
                       {
                           "count": 1,
                           "value": "application/vnd.org.cnx.module"
                       }
                   ]
               },
               {
                   "tag": "keyword",
                   "values": [
                       {
                           "count": 1,
                           "value": "college physics"
                       },
                       {
                           "count": 1,
                           "value": "introduction"
                       },
                       {
                           "count": 1,
                           "value": "physics"
                       }
                   ]
               },
               {
                   "tag": "subject",
                   "values": [
                       {
                           "count": 1,
                           "value": "Mathematics and Statistics"
                       }
                   ]
               }
           ],
           "total": 1
       }
   }

 