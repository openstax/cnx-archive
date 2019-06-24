from functools import wraps

import psycopg2
from pyramid import httpexceptions
from pyramid.view import view_config

from ..database import SQL, db_connect
from ..utils import (
    IdentHashShortId, IdentHashMissingVersion, IdentHashSyntaxError,
    split_ident_hash, COLLECTION_MIMETYPE, join_ident_hash
)
from .helpers import get_uuid, get_latest_version


# #################### #
#        Helpers       #
# #################### #


NAMESPACES = {
    'cnx': 'http://cnx.rice.edu/cnxml',
    'c': 'http://cnx.rice.edu/cnxml',
    'system': 'http://cnx.rice.edu/system-info',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'mml': 'http://www.w3.org/1998/Math/MathML',
    'm': 'http://www.w3.org/1998/Math/MathML',
    'md': 'http://cnx.rice.edu/mdml',
    'qml': 'http://cnx.rice.edu/qml/1.0',
    'bib': 'http://bibtexml.sf.net/',
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'h': 'http://www.w3.org/1999/xhtml',
    'data': 'http://www.w3.org/TR/html5/dom.html#custom-data-attribute',
    'cmlnle': 'http://katalysteducation.org/cmlnle/1.0',
}


# #################### #
#     Route method     #
# #################### #


def extract_params_as_args(f):
    """extracts the query parameters as arguments to the view function"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        request = args[0]
        id = request.params.get('id')
        q = request.params.get('q')

        if not id or not q:
            raise httpexceptions.HTTPBadRequest(
                'You must supply both a UUID and an xpath'
            )

        kwargs['id'] = id
        kwargs['q'] = q
        return f(*args, **kwargs)

    return wrapper


@view_config(route_name='xpath', request_method='GET',
             http_cache=(60, {'public': True}))
@view_config(route_name='xpath-json', request_method='GET',
             http_cache=(60, {'public': True}))
@extract_params_as_args
def xpath(request, id, q):
    """View for the route. Determines UUID and version from input request
    and determines the type of UUID (collection or module) and executes
    the corresponding method."""
    ident_hash = id
    xpath_string = q

    try:
        uuid, version = split_ident_hash(ident_hash)
    except IdentHashShortId as e:
        uuid = get_uuid(e.id)
        version = e.version
    except IdentHashMissingVersion as e:
        uuid = e.id
        version = get_latest_version(e.id)
    except IdentHashSyntaxError:
        raise httpexceptions.HTTPBadRequest

    resp = request.response
    resp.status = "200 OK"
    return resp
