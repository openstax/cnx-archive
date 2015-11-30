from cnxepub import flatten_tree_to_ident_hashes
from StringIO import StringIO
from lxml import etree

__all__ = ('json2colxml','load_collection')

def load_collection(file_path):
    with open(file_path,'r') as f:
        collection=etree.parse(f)
    return collection

collection_template = load_collection('cnxarchive/utils/col_template.xml')

from lxml.builder import ElementMaker

DEFAULT_NAMESPACE="http://cnx.rice.edu/collxml"

DEFAULT_NSMAP={'md': 'http://cnx.rice.edu/mdml',
       'cc': 'http://web.resource.org/cc/',
       'bib': 'http://bibtexml.sf.net/',
       'm': 'http://www.w3.org/1998/Math/MathML',
       'cnx': 'http://cnx.rice.edu/cnxml',
       'q': 'http://cnx.rice.edu/qml/1.0',
       'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
       'cnxml': 'http://cnx.rice.edu/cnxml',
       'col': 'http://cnx.rice.edu/collxml',
       'xhtml': 'http://www.w3.org/1999/xhtml',
       'cnxorg': 'http://cnx.rice.edu/system-info',}

def json2colxml(json):
#    colxml = flatten_tree_to_ident_hashes(json)
#    collection = collection_template
    COL = ElementMaker(namespace=DEFAULT_NAMESPACE, nsmap=DEFAULT_NSMAP)
#    M = ElementMaker(namespace='http://cnx.rice.edu/mdml', nsmap={'md':'http://cnx.rice.edu/mdml'})
    META = ElementMaker()
    MD = ElementMaker(namespace='http://cnx.rice.edu/mdml', nsmap={'md':'http://cnx.rice.edu/mdml'})
    metadata=META('metadata', {'mdml-version':'5.0'},
                        MD.repository("http://cnx.org/content"),
                        MD.content_url(),
                        MD.title(json['title']),
                        MD.version(),
                        MD.created(),
                        MD.revised(),
                        MD.actors( 
                            MD.person(
                                MD.firstname(),
                                MD.surname(),
                                MD.fullname(),
                                MD.email(),
                            ),
                            MD.roles(
                            )
                        ),
                        MD.keywordlist(),
                        MD.subjectlist(),
                        MD.abstract(),
                        MD.language(),
                    )
    parameters= COL.parameters()
    content = COL.content()
    
    for con in json['tree']['contents']:
        document = {'document': con['id'].split('@')[0]}
        try:
            version =  {'version': con['id'].split('@')[1]}
            element = COL.module(
                   document,
                   version,
                   MD.title(con['title'])
                   )
        except IndexError:
            element = COL.module(
                   document,
                   MD.title(con['title'])
                   )

        content.append(element)
 

    collection= COL.collection(
                   metadata,
                   parameters,
                   content
                )

    return collection
"""
  <md:actors>


<md:person userid="sstarks">
<md:firstname>Scott</md:firstname>
<md:surname>Starks</md:surname>
<md:fullname>Scott Starks</md:fullname>
<md:email>sstarks@utep.edu</md:email>
</md:person>

</md:actors>
  <md:roles>
    <md:role type="author">sstarks</md:role>
    <md:role type="maintainer">sstarks</md:role>
    <md:role type="licensor">sstarks</md:role>


  </md:roles>

"""           
#    metadata = ElementMaker(namespace=DEFAULT_NSMAP['md'], nsmap={'md':DEFAULT_NSMAP['md']})
#   collection.metadata("hi")


