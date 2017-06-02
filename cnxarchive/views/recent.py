import psycopg2
from pyramid import httpexceptions
from pyramid.view import view_config
from calendar import month_name
from pyramid.threadlocal import get_current_registry

from .. import config

# What should actually be the varibales in view config???
@view_config(route_name='recent', request_method='GET',
             accept="application/json",
             renderer='json', permission='read') # originally was renderer='json'??,
def get_recent(request):
    num_entries = 10    # later can set there variables based on args in url
    start_entry = 0
    settings = request.registry.settings
    statement = """
                SELECT name, revised, authors, abstract,
                'http://cnx.org/contents/'||ident_hash( uuid, major_version, minor_version) AS link
                FROM latest_modules
                JOIN abstracts ON latest_modules.abstractid = abstracts.abstractid
                WHERE portal_type in ('Collection', 'Module')
                ORDER BY revised DESC
                LIMIT {};
                """.format(num_entries)
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(statement)
                search_results = cursor.fetchall()

    latest_modules = []
    titles = ["name", "revised", "authors", "abstract", "link"]
    for i in range(len(search_results)):
        latest_modules.append(dict(zip(titles, search_results[i])))
    # set dates to be correct format
    # get authors from persons table
    for module in latest_modules:
        module['revised'] = format_date(module['revised'])
        module['authors'] = format_author(module['authors'], settings)

    return latest_modules


def format_author(personids, settings):
    """
    Takes a list of personid's and searches in the persons table to get their
    full names and returns a list of the full names as a string.
    """
    personids_string = "("
    for i in range(len(personids) - 1):
        personids_string += "'{},'".format(peronids[i])
    personids_string += "'{}'".format(personids[-1])
    personids_string += ")"
    statement = """
                SELECT fullname
                FROM persons
                WHERE personid IN {};
                """.format(personids_string)
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(statement)
                authors_list = cursor.fetchall()
    return str(authors_list)[1:-1]


def format_date(date):
    """
    date is in the for datetime.datetime
    returns date as a string in the form 'May 30, 2017 at 3:03 PM'
    """
    date_string = date.isoformat()
    day = date_string.split("T")[0]
    day = day.split("-")
    month = month_name[int(day[1])]

    time = date_string.split("T")[1]
    hour = int(time[:2])
    if hour < 12:
        period = "AM"
    else:
        hour = hour - 12
        period = "PM"
    if hour == 0:
        hour = 12
    minute = time[3:5]
    return "{} {}, {} at {}:{} {}".\
        format(month, day[2], day[0], hour, minute, period)
