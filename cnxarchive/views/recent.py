import psycopg2
from pyramid import httpexceptions
from pyramid.view import view_config
import calendar
from pyramid.threadlocal import get_current_registry

from .. import config

# What should actually be the varibales in view config???
@view_config(route_name='recent', request_method='GET',
             accept="application/json", ## what does this mean???
             renderer='recent.html', permission='') # originally was renderer='json',
def get_recent(request):
    settings = request.registry.settings
    statement = """
                SELECT name, revised, authors, abstract, uuid, major_version, minor_version
                FROM latest_modules
                JOIN abstracts ON latest_modules.abstractid = abstracts.abstractid
                ORDER BY revised DESC
                LIMIT 10;
                """
    with psycopg2.connect(settings[config.CONNECTION_STRING]) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(statement)
                latest_modules_lists = cursor.fetchall()

    latest_modules = []
    titles = ["name", "revised", "authors", "abstract", "uuid", "major_version", "minor_version"]
    for i in range(len(search_results)):
        latest_modules.append(dict(zip(titles, search_results[i])))
    # set dates to be correct format
    # get authors from persons table and format string, set the link uuid
    # major_version, minor_version
    for module in latest_modules:
        module['revised'] = format_date(module['revised'])
        module['authors'] = format_author(module['authors'])
        module['link'] = format_link(module['uuid'], module['major_version'],
                                     module['minor_version'])

    return latest_modules


def format_link(uuid, major_version, minor_version):
    link = "{}@{}"uuid
    if minor_version:
        link += "." + minor_version
    return link

def format_author(personids):
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
    day = date_string.split(" ")[0]
    day = day.split("-")
    month = calendar.month_name[int(day[1])]

    time = date_string.split(" ")[1]
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
