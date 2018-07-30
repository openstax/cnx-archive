OAI Feed
==========

The OAI feed is used to harvest or query metadata about OpenStax CNX content. It is based on the [OAI-PMH spec](https://www.openarchives.org/OAI/openarchivesprotocol.html).

Example URLs
------------

** API Location **
https://archive.cnx.org/feeds/oai

**List of metadata formats**
https://archive.cnx.org/feeds/oai?verb=ListMetadataFormats

**List of identifiers from now until a specified date**
https://archive.cnx.org/feeds/oai?verb=ListIdentifiers&metadataPrefix=cnx_dc&until=2017-01-01

**List of records in a date range**
https://archive.cnx.org/feeds/oai?verb=ListRecords&metadataPrefix=cnx_dc&from=2017-01-01&until=2017-07-01

**Record for a specified record identifier**
https://archive.cnx.org/feeds/oai?verb=GetRecord&metadataPrefix=cnx_dc&identifier=oai:archive.cnx.org:031da8d3-b525-429c-80cf-6c8ed997733a
