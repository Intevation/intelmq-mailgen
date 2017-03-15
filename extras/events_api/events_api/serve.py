#!/usr/bin/env python3
"""Serve IntelMQ Events

Requires hug (http://www.hug.rest/)

Copyright (C) 2017 by Bundesamt für Sicherheit in der Informationstechnik

Software engineering by Intevation GmbH

This program is Free Software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Author(s):
    * Bernhard E. Reiter <bernhard@intevation.de>
    * Dustin Demuth <dustin.demuth@intevation.de>

TODO:
    - Paging needs to be considered, it's not implemented yet
    - To start, all queries will be AND concatenated. OR-Queries can be introduced later.
    - Search for and in directives

"""

import json
import logging
import os
import sys
# FUTURE the typing module is part of Python's standard lib for v>=3.5
# try:
#    from typing import Tuple, Union, Sequence, List
# except:
#    pass

from falcon import HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_SERVICE_UNAVAILABLE, HTTP_INTERNAL_SERVER_ERROR
import hug
import psycopg2
import datetime
from psycopg2.extras import RealDictCursor


log = logging.getLogger(__name__)
# adding a custom log level for even more details when diagnosing
DD = logging.DEBUG-2
logging.addLevelName(DD, "DDEBUG")

EXAMPLE_CONF_FILE = r"""
{
  "libpg conninfo":
    "host=localhost dbname=eventdb user=apiuser password='USER\\'s DB PASSWORD'",
  "logging_level": "INFO"
}
"""

EVENTDB_TABLE_NAME = "events"

ENDPOINT_PREFIX = '/api/events'


def read_configuration() -> dict:
    """Read configuration file.

    If the environment variable EVENTDB_SERVE_CONF_FILE exist, use it
    for the file name. Otherwise uses a default.

    TODO:
        Move this to a lib which can be used as a common function
        for contact_db_api and other extensions.
        Maybe the Endpoint-Prefix can be a parameter for this.

    Returns:
        The configuration values, possibly containing more dicts.

    Notes:
      Design rationale:
        * Provies an "okay" separation from config and code.
        * Better than intelmq-mailgen which has two hard-coded places
          and merge code for the config.
        * (Inspired by https://12factor.net/config.) But it is not a good
          idea to put credential information in the commandline or environment.
        * We are using json for the configuration file format and not
          Python's configparser module to stay more in line with intelmq's
          overall design philosophy to use json for configuration files.
    """
    config = None
    config_file_name = os.environ.get(
                        "EVENTDB_SERVE_CONF_FILE",
                        "/etc/intelmq/eventdb-serve.conf")

    if os.path.isfile(config_file_name):
        with open(config_file_name) as config_handle:
                config = json.load(config_handle)

    return config if isinstance(config, dict) else {}


eventdb_conn = None
# Using a global object for the database connection
# must be initialised once


def open_db_connection(dsn: str):
    """ Open the Connection to the EventDB

    Args:
        dsn: a Connection - String

    Returns: a Database Connection

    """
    global eventdb_conn

    eventdb_conn = psycopg2.connect(dsn=dsn)
    return eventdb_conn


def __rollback_transaction():
    global eventdb_conn
    log.log(DD, "Calling rollback()")
    eventdb_conn.rollback()

QUERY_EVENT_SUBQUERY = {
    'id': 'id = %s',
    # Time
    'time-observation_before': '"time.observation" < %s',
    'time-observation_before_encl': '"time.observation" <= %s',
    'time-observation_after': '"time.observation" > %s',
    'time-observation_after_encl': '"time.observation" > %s',
    'time-source_before': '"time.source" < %s',
    'time-source_before_encl': '"time.source" <= %s',
    'time-source_after': '"time.source" > %s',
    'time-source_after_encl': '"time.source" > %s',
    # Source
    'source-ip_in_sn': '"source.ip" <<= %s',
    'source-ip_is': '"source.ip" = %s',
    'source-asn_is': '"source.asn" = %s',
    'source-fqdn_is': '"source.fqdn" = %s',
    'source-fqdn_icontains': '"source.fqdn" ILIKE %s',

    # Destinations
    'destination-ip_in_sn': '"destination.ip" <<= %s',
    'destination-ip_is': '"destination.ip" = %s',
    'destination-asn_is': '"destination.asn" = %s',
    'destination-fqdn_is': '"destination.fqdn" = %s',
    'destination-fqdn_icontains': '"destination.fqdn" ILIKE %s',

    # Classification
    'classification-taxonomy_is': '"classification.taxonomy" = %s',
    'classification-taxonomy_icontains': '"classification.taxonomy" ILIKE %s',
    'classification-type_is': '"classification.type" = %s',
    'classification-type_icontains': '"classification.type" ILIKE %s',
    'classification-identifier_is': '"classification.identifier" = %s',
    'classification-identifier_icontains': '"classification.identifier" ILIKE %s',
    'malware-name_is': '"malware.name" = %s',
    'malware-name_icontains': '"malware.name" ILIKE %s',

    # Feed
    'feed-provider_is': '"feed.provider" = %s',
    'feed-provider_icontains': '"feed.provider" ILIKE %s',
    'feed-name_is': '"feed.name" = %s',
    'feed-name_icontains': '"feed.name" ILIKE %s',
}


def query_get_subquery(q: str):
    """ Return the query-Statement from the QUERY_EVENT_SUBQUERY

    Basically this is a getter for the dict...

    Args:
        q: A Key which can be found in QUERY_EVENT_SUBQUERY

    Returns: The subquery from QUERY_EVENT_SUBQUERY

    """
    r = QUERY_EVENT_SUBQUERY.get(q, '')
    if r:
        return r
    else:
        raise ValueError('The Query-Paramter you asked for is not supported.')


def query_build_subquery(q: str, p: str):
    """Resolves the Query-Operaton and the Parameter into a tuple of SQL and the parameter

    Args:
        q: the column which should match the search value
        p: the search value

    Returns: a tuple containing Query an Search Value

    """
    t = (query_get_subquery(q), p)
    return t


def query_build_query(params):
    """

    Args:
        params:

    Returns: An Array of tuples

    """
    queries = []
    for key in params:
        queries.append(query_build_subquery(key, params[key]))
    return queries


def query_prepare_export(q):
    """ Prepares a Query-string in order to Export Everything from the DB

    Args:
        q: An array of Tuples created with query_build_query

    Returns: A Tuple consisting of a query sting and an array of parameters.

    """
    q_string = "SELECT * FROM events"  # TODO maybe events should be a variable...
    params = []
    # now iterate over q (which had to be created with query_build_query
    # previously) and should be a list of tuples an concatenate the resulting query.
    # and a list of query parameters
    counter = 0
    for subquerytuple in q:
        if counter > 0:
            q_string = q_string + " AND " + subquerytuple[0]
            params.append(subquerytuple[1])
        else:
            q_string = q_string + " WHERE " + subquerytuple[0]
            params.append(subquerytuple[1])
        counter += 1
    return q_string, params


def query_prepare_search(q):
    """ Prepares a Query-string in order to Export Everything from the DB

    Args:
        q: An array of Tuples created with query_build_query

    Returns: A Tuple consisting of a query sting and an array of parameters.

    """
    q_string = "SELECT id , " \
               " \"time.observation\", " \
               " \"time.source\", " \
               " \"source.ip\", " \
               " \"destination.ip\", " \
               " \"classification.taxonomy\", " \
               " \"classification.type\", " \
               " \"classification.identifier\", " \
               " \"malware.name\", " \
               " \"feed.provider\", "\
               " \"feed.name\" " \
               " FROM events"  # TODO maybe events should be a variable...

    params = []
    # now iterate over q (which had to be created with query_build_query
    # previously) and should be a list of tuples an concatenate the resulting query.
    # and a list of query parameters
    counter = 0
    for subquerytuple in q:
        if counter > 0:
            q_string = q_string + " AND " + subquerytuple[0]
            params.append(subquerytuple[1])
        else:
            q_string = q_string + " WHERE " + subquerytuple[0]
            params.append(subquerytuple[1])
        counter += 1
    return q_string, params


def query_prepare_stats(q, interval = 'day'):
    """ Prepares a Query-string for statistics

    Args:
        q: An array of Tuples created with query_build_query
        interval: 'month, 'day' or 'hour'

    Returns: A Tuple consisting of a query sting and an array of parameters.

    """

    if interval not in ('month', 'day', 'hour'):
        raise ValueError

    trunc = "date_trunc('%s', \"time.source\")" % (interval,)

    q_string = "SELECT %s, count(*) " \
               "FROM events " % (trunc, )  # TODO maybe events should be a variable...

    params = []
    # now iterate over q (which had to be created with query_build_query
    # previously) and should be a list of tuples an concatenate the resulting query.
    # and a list of query parameters
    counter = 0
    for subquerytuple in q:
        if counter > 0:
            q_string = q_string + " AND " + subquerytuple[0]
            params.append(subquerytuple[1])
        else:
            q_string = q_string + " WHERE " + subquerytuple[0]
            params.append(subquerytuple[1])
        counter += 1
    q_string = q_string + " GROUP BY %s" % (trunc, )
    return q_string, params

def query(prepared_query):
    """ Queries the Database for Events

    Args:
        prepared_query: A QueryString, Paramater pair created with query_prepare

    Returns: The results of the databasequery in JSON-Format.

    """
    global eventdb_conn

    # psycopgy2.4 does not offer 'with' for cursor()
    # FUTURE use with
    cur = eventdb_conn.cursor(cursor_factory=RealDictCursor)

    operation = prepared_query[0]
    parameters = prepared_query[1]
    log.info(cur.mogrify(operation, parameters))
    cur.execute(operation, parameters)
    log.log(DD, "Ran query={}".format(repr(cur.query.decode('utf-8'))))
    # description = cur.description
    results = cur.fetchall()

    return results


@hug.startup()
def setup(api):
    config = read_configuration()
    if "logging_level" in config:
        log.setLevel(config["logging_level"])
    open_db_connection(config["libpg conninfo"])
    log.debug("Initialised DB connection for events_api.")


@hug.get(ENDPOINT_PREFIX, examples="id=1")
# @hug.post(ENDPOINT_PREFIX)
def getEvent(response, id: int = None):
    """Return one Event identifid by ID

    Args:
        response: A HUG response object...
        id: The ID of an event

    Returns: If existing one event of the EventDB

    """
    if id:
        param =  {"id": id}
    else:
        response.status = HTTP_BAD_REQUEST
        return {"error": "You need to provide an id."}

    querylist = query_build_query(param)

    prep = query_prepare_export(querylist)

    try:
        return query(prep)
    except psycopg2.Error as e:
        log.error(e)
        __rollback_transaction()
        response.status = HTTP_INTERNAL_SERVER_ERROR
        return {"error": "The query could not be processed."}


@hug.get(ENDPOINT_PREFIX + '/search', examples="time-observation_after=2017-03-01&time-observation_before=2017-03-01")
# @hug.post(ENDPOINT_PREFIX + '/search')
def search(response, **params):
    """Search for events

    Args:
        response: A HUG response object...
        **params: Queries from QUERY_EVENT_SUBQUERY

    Returns: A subset of the most likely most important fields of the events which are matching the query.

    """
    for param in params:
        # Test if the parameters are sane....
        try:
            query_get_subquery(param)
        except ValueError:
            response.status = HTTP_BAD_REQUEST
            return {"error": "At least one of the queryparameters is not allowed"}

    if not params:
        response.status = HTTP_BAD_REQUEST
        return {"error": "Queries without parameters are not supported"}

    querylist = query_build_query(params)

    prep = query_prepare_search(querylist)

    try:
        return query(prep)
    except psycopg2.Error as e:
        log.error(e)
        __rollback_transaction()
        response.status = HTTP_INTERNAL_SERVER_ERROR
        return {"error": "The query could not be processed."}


@hug.get(ENDPOINT_PREFIX + '/stats', examples="malware-name_is=nymaim")
# @hug.post(ENDPOINT_PREFIX + '/export')
def stats(response, **params):
    """ This interface returns a statistic all events matching the query parameters

    Args:
        response: A HUG response object...
        **params: Queries from QUERY_EVENT_SUBQUERY

    Returns: If existing a statiustical view on the amount of events per time-frame

    """
    today = datetime.date.today()

    # TODO: Make the Timebox configurable

    params["time-observation_after"] = today - datetime.timedelta(days=1),
    params["time-observation_before"] = today + datetime.timedelta(days=1)

    # remove other time-params which  might conflict this.
    if params.get("time-observation_after_encl"):
        del params["time-observation_after_encl"]
    if params.get("time-observation_before_encl"):
        del params["time-observation_before_encl"]

    for param in params:
        # Test if the parameters are sane....

        try:
            query_get_subquery(param)
        except ValueError:
            response.status = HTTP_BAD_REQUEST
            return {"error": "At least one of the queryparameters is not allowed"}

    if not params:
        response.status = HTTP_BAD_REQUEST
        return {"error": "Queries without parameters are not supported"}

    querylist = query_build_query(params)

    # TODO : Make the Resolution 'day' configurable

    prep = query_prepare_stats(querylist, 'day')

    try:
        return query(prep)
    except psycopg2.Error as e:
        log.error(e)
        __rollback_transaction()
        response.status = HTTP_INTERNAL_SERVER_ERROR
        return {"error": "The query could not be processed."}


@hug.get(ENDPOINT_PREFIX + '/export', examples="time-observation_after=2017-03-01&time-observation_before=2017-03-01")
# @hug.post(ENDPOINT_PREFIX + '/export')
def export(response, **params):
    """ This interface exports all events matching the query parameters

    Args:
        response: A HUG response object...
        **params: Queries from QUERY_EVENT_SUBQUERY

    Returns: If existing all events of the EventDB which are matching the query

    """
    for param in params:
        # Test if the parameters are sane....
        try:
            query_get_subquery(param)
        except ValueError:
            response.status = HTTP_BAD_REQUEST
            return {"error": "At least one of the queryparameters is not allowed"}

    if not params:
        response.status = HTTP_BAD_REQUEST
        return {"error": "Queries without parameters are not supported"}

    querylist = query_build_query(params)

    prep = query_prepare_export(querylist)

    try:
        return query(prep)
    except psycopg2.Error as e:
        log.error(e)
        __rollback_transaction()
        response.status = HTTP_INTERNAL_SERVER_ERROR
        return {"error": "The query could not be processed."}



def main():
    """ Main function of this modul

    Returns: Nothing....

    """
    if len(sys.argv) > 1 and sys.argv[1] == '--example-conf':
        print(EXAMPLE_CONF_FILE)
        exit()

    config = read_configuration()
    print("config = {}".format(config,))
    if "logging_level" in config:
        log.setLevel(config["logging_level"])

    print("log.name = \"{}\"".format(log.name))
    print("log effective level = \"{}\"".format(
        logging.getLevelName(log.getEffectiveLevel())))

    global eventdb_conn
    eventdb_conn = open_db_connection(config["libpg conninfo"])

    # TODO: Maybe add a search interface for the CLI
    # params={'t.o_after': '2017-03-01', 's.ip_in_sn': '31.25.41.74'}
    # prep = query_prepare(query_build_query(params))
    # return query(prep)
