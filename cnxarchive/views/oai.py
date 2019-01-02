# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013-2018, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from datetime import datetime
from re import compile

import psycopg2.extras
from pyramid.view import view_config

from .. import config
from ..database import db_connect
from ..utils import rfc822


# ################### #
#     OAI HELPERS     #
# ################### #

def _setFromUntil(request):
    arguments = []
    where = ""
    if 'from' in request.GET.keys():
        where = "WHERE revised>=(%s)"
        arguments.append(request.GET.get('from'))
    if 'until' in request.GET.keys():
        arguments.append(request.GET.get('until'))
        if where == "":
            where = "WHERE revised<=(%s)"
        else:
            where += " AND revised<=(%s)"
    return where, arguments


def _databaseDictResults(statement, arguments):
    with db_connect() as db_c:
        cur = db_c.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(statement, vars=arguments)
        search_results = cur.fetchall()
    return search_results


def _parseOaiArguments(verb, request):
    VERBS = {'GetRecord': {'required': ['verb', 'identifier',
                                        'metadataPrefix'],
                           'optional': []},
             'Identify': {'required': ['verb'],
                          'optional': []},
             'ListIdentifiers': {'required': ['verb', 'metadataPrefix'],
                                 'optional': ['from', 'until', 'set']},
             'ListMetadataFormats': {'required': ['verb'],
                                     'optional': ['identifier']},
             'ListRecords': {'required': ['verb', 'metadataPrefix'],
                             'optional': ['from', 'until', 'set']},
             'ListSets': {'required': ['verb'],
                          'optional': ['resumptionToken']},
             }
    # verify that the arguments given are correct, otherwise set an error
    if not(verb in VERBS.keys()):
        return {'code': 'badVerb',
                'message': 'Illegal verb: Legal verbs are: {}'.
                           format(VERBS.keys())}
    # check to make sure only correct arguments have been passed
    all_query_vars = request.GET.keys()
    required = VERBS[verb]['required']
    optional = VERBS[verb]['optional']
    missing = list(set(required) - set(all_query_vars))
    if missing:
        return {'code': 'badArgument',
                'message': 'Required argument {} missing'.format(missing)}
    extras = list(set(all_query_vars) - (set(required) | set(optional)))
    if extras:
        return {'code': 'badArgument',
                'message': 'Illegal arguments: {}'. format(extras)}
    return "No errors"


def _verifyMetadataPrefix(request):
    prefixes = ['oai_dc', 'ims1_2_1', 'cnx_dc']
    prefix = request.GET.get('metadataPrefix')
    if prefix not in prefixes:
        return {'error': {'code': 'cannotDisseminateFormat',
                          'message': 'metadataPrefix {} not supported'.
                                     format(prefix)}}
    return {'metadataPrefix': prefix}


def _noRecordsMatchError():
    return {'error': {'code': 'noRecordsMatch',
                      'message': 'No matches for the given request'}}


def _formatOaiResults(results, request):
    if len(results) == 0:
        return _noRecordsMatchError()
    for result in results:
        result['name'] = result['name'].decode('utf-8')
        result['abstract'] = result['abstract'].decode('utf-8')
        result['authors'] = _decodeArray(result['authors'])
        result['maintainers'] = _decodeArray(result['maintainers'])
        result['translators'] = _decodeArray(result['translators'])
        result['link'] = request.route_url('content',
                                           ident_hash=result['link'])
        new_authors = []
        for i in range(len(result['authors'])):
            new_authors.append({'fullname': result['authors'][i],
                                'email': result['author_emails'][i]})
        result['authors'] = new_authors
    return {'results': results}


def _decodeArray(result_array):
    decoded = []
    for result in result_array:
        decoded.append(result.decode('utf-8'))
    return decoded


def _oaiGetBaseStatement():
    return """
             name, created, revised, uuid, uuid as link, portal_type, language,
             concat(major_version, '.', minor_version) as version,
             ARRAY(SELECT k.word FROM keywords as k, modulekeywords
                as mk WHERE mk.module_ident = lm.module_ident AND
                    mk.keywordid = k.keywordid) as keywords,
             ARRAY(SELECT tags.tag FROM tags, moduletags
                as mt WHERE mt.module_ident = lm.module_ident AND
                    mt.tagid = tags.tagid) as subjects,
             ARRAY(SELECT fullname as fields FROM persons WHERE
                persons.personid = ANY (lm.authors)) as authors,
             ARRAY(SELECT email as fields FROM persons WHERE
                persons.personid = ANY (lm.authors)) as author_emails,
             ARRAY(SELECT fullname FROM persons WHERE persons.personid =
                ANY (lm.maintainers)) as maintainers,
             ARRAY(SELECT fullname FROM persons WHERE exists
                (SELECT true FROM moduleoptionalroles as mor
                    JOIN roles as r ON mor.roleid=r.roleid
                        WHERE mor.module_ident = lm.module_ident AND
                        r.roleparam='translator' AND
                        persons.personid = ANY (mor.personids)))
                as translators,
             (COALESCE((SELECT abstract FROM abstracts WHERE
                lm.abstractid = abstracts.abstractid), '')) as abstract,
             (SELECT url FROM licenses
                WHERE lm.licenseid = licenses.licenseid) as licenses_url
                           """


def do_Identify(request):
    return {'host': request.host,
            'adminEmail': "support@openstax.org",
            'repository': config.REPOSITORY_NAME}


def do_ListMetadataFormats(request):
    METADATA_FORMATS = [
        {'prefix': 'oai_dc',
         'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
         'namespace': 'http://www.openarchives.org/OAI/2.0/oai_dc/'},
        {'prefix': 'ims1_2_1',
         'schema': 'http://www.imsglobal.org/xsd/imsmd_v1p2p4.xsd',
         'namespace': 'http://www.imsglobal.org/xsd/imsmd_v1p2'},
        {'prefix': 'cnx_dc',
         'schema': '/http://cnx.rice.edu/technology/cnx_dc/schema/xsd/1.0/'
                   'cnx-dc-extension.xsd',
         'namespace': 'http://cnx.rice.edu/cnx_dc/'}
        ]
    return {'results': METADATA_FORMATS}


def do_ListSets(request):
    # return error, ListSets currently not supported
    return {'error': {'code': 'noSetHierarchy',
                      'message': 'ListSets not currently supported'}}


def do_ListIdentifiers(request):
    new_vars = _verifyMetadataPrefix(request)
    if 'error' in new_vars.keys():
        return new_vars
    where, arguments = _setFromUntil(request)
    statement = """
                SELECT revised, uuid
                FROM latest_modules {}
                ORDER BY revised;
                """.format(where)
    search_results = _databaseDictResults(statement, arguments)
    if len(search_results) == 0:
        return _noRecordsMatchError()
    new_vars.update({'results': search_results})
    return new_vars


def do_GetRecords(request):
    new_vars = _verifyMetadataPrefix(request)
    if 'error' in new_vars.keys():
        return new_vars
    identifier = str(request.GET.get('identifier'))
    idDoesNotExist = {'code': 'idDoesNotExist',
                      'message': "id does not exist {}".
                                 format(identifier)}
    pattern = ("oai:" + request.host + ":[0-9a-z]{8}-[0-9a-z]{4}-"
               "[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}$")
    if not compile(pattern).match(identifier):
        return {'error': idDoesNotExist}
    uuid = identifier.split(':')[-1]
    statement = "SELECT" + _oaiGetBaseStatement()
    statement += "FROM latest_modules as lm  WHERE uuid=(%s);"
    results = _databaseDictResults(statement, (uuid,))
    if len(results) == 0:
        return {'error': idDoesNotExist}
    new_vars.update(_formatOaiResults(results, request))
    return new_vars


def do_ListRecords(request):
    new_vars = _verifyMetadataPrefix(request)
    if 'error' in new_vars.keys():
        return new_vars
    where, arguments = _setFromUntil(request)
    statement = "SELECT" + _oaiGetBaseStatement()
    statement += "FROM latest_modules as lm {} ORDER BY revised;".format(where)
    results = _databaseDictResults(statement, arguments)
    new_vars.update(_formatOaiResults(results, request))
    return new_vars


# ################## #
#      OAI VIEW      #
# ################## #


@view_config(route_name='oai', request_method='GET',
             renderer='templates/oai_verbs.xml',
             http_cache=(60, {'public': True}))
def oai(request):
    request.response.headers = {'Content-Type': 'text/xml; charset=UTF-8'}

    return_vars = {}
    return_vars['dateTime'] = rfc822(datetime.now().time())
    return_vars['baseURL'] = request.path_url
    return_vars['host'] = request.host
    return_vars['query_request'] = []
    for var in request.GET:
        return_vars['query_request'].append({'name': var,
                                             'val': request.GET[var]})
    verb = request.GET.get('verb')
    parse_results = _parseOaiArguments(verb, request)
    return_vars['verb'] = verb
    if parse_results != "No errors":
        return_vars['error'] = parse_results
        return return_vars
    oaiQuery = {'Identify': do_Identify,
                'ListMetadataFormats': do_ListMetadataFormats,
                'ListSets': do_ListSets,
                'ListIdentifiers': do_ListIdentifiers,
                'GetRecord': do_GetRecords,
                'ListRecords': do_ListRecords}
    return_vars.update(oaiQuery[verb](request))
    if 'error' in return_vars.keys():
        return_vars['verb'] = 'error'
    return return_vars
