#!/usr/bin/env python3
"""Serve intelmq-certbund-contact db api via wsgi.

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
    Bernhard E. Reiter <bernhard@intevation.de>


Design rationale:
    Our services shall be accessed by https://github.com/Intevation/intelmq-fody
    so our "endpoints" should be reachable from the same ip:port as
    the checkticket endpoints.

    We need location and credentials for the database holding the contactdb.
    checkticket.py [1] (a hug based backend) solves this problem by reusing
    the intelmq-mailgen configuration to access the 'intelmq-events' database.
    This serving part need to access a different database 'contactdb', thus
    we start with our on configuration.

    [1] https://github.com/Intevation/intelmq-mailgen/blob/master/extras/checkticket-spa/checkticket.py

"""
import json
import logging
import os
import sys
#FUTURE the typing module is part of Python's standard lib for v>=3.5
#try:
#    from typing import Tuple, Union, Sequence, List
#except:
#    pass

from falcon import HTTP_BAD_REQUEST
import hug
import psycopg2
from psycopg2.extras import RealDictCursor



log = logging.getLogger(__name__)

def read_configuration() -> dict:
    """Read configuration file.

    If the environment variable CONTACTDB_SERVE_CONF_FILE exist, use it
    for the file name. Otherwise uses a default.

    Returns:
        The configuration values, possibly containing more dicts.

    Notes:
      Design rationale
      ----------------
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
                        "CONTACTDB_SERVE_CONF_FILE",
                        "/etc/intelmq/contactdb-serve.conf")

    if os.path.isfile(config_file_name):
        with open(config_file_name) as config_handle:
                config = json.load(config_handle)

    return config if isinstance(config, dict) else {}

EXAMPLE_CONF_FILE = r"""
{
  "libpg conninfo":
    "host=localhost dbname=contactdb user=intelmq password='USER\\'s DB PASSWORD'",
  "logging_level": "INFO"
}
"""

ENDPOINT_PREFIX = '/api/contactdb'

# Using a global object for the database connection
# must be initialised once
contactdb_conn = None

def open_db_connection(dsn:str):
    global contactdb_conn

    contactdb_conn = psycopg2.connect(dsn=dsn)
    return contactdb_conn

def __commit_transaction():
    global contactdb_conn
    contactdb_conn.commit()

def __rollback_transaction():
    global contactdb_conn
    contactdb_conn.rollback()


# FUTURE once typing is available
#def _db_query(operation:str, parameters:Union[dict, list]=None,
#              end_transaction:bool=True) -> Tuple(list, list):
def _db_query(operation:str, parameters=None, end_transaction:bool=True):
    """Does an database query.

    Creates a cursor from the global database connection, runs
    the query or command the fetches all results.

    Parameters:
        operation: The query to be used by psycopg2.cursor.execute()
        parameters: for the sql query
        end_transaction: set to False to do subsequent queries in the same
            transaction.

    Returns:
        Tuple[list, List[psycopg2.extras.RealDictRow]]: description and results.
    """
    global contactdb_conn

    description = None

    # pscopgy2.4 does not offer 'with' for cursor()
    # FUTURE use with
    cur = contactdb_conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(operation, parameters)
    description = cur.description
    results = cur.fetchall()

    if end_transaction:
        __commit_transaction()

    cur.close()

    return (description, results)

def __db_query_organisation_ids(operation_str:str,  parameters=None):
    """Inquires organisation_ids for a specific query.

    Parameters:
        operation(str): must be a psycopg2 execute operation string that
            only returns an array of ids "AS organisation_ids" or nothing
            it has to contain '{0}' format placeholders for the table variants

    Returns:
        Dict("auto":list, "manual":list): lists of organisation_ids that
            where manually entered or imported automatically
    """
    orgs = {}

    description, results = _db_query(operation_str.format(""), parameters)
    orgs["manual"] = results[0]["organisation_ids"] if len(results)==1 else []
    description, results = _db_query(operation_str.format("_automatic"),
                                     parameters)
    orgs["auto"] = results[0]["organisation_ids"] if len(results)==1 else []

    return orgs


def __db_query_org(org_id:int, table_variant:str):
    """Returns details for an organisaion.

    Parameters:
        org_id:int: the organisation id to be queries
        table_variant: either "" or "_automatic"

    Returns:
        dict: containing the organisation and additional keys
            'asns' and 'contacts'
    """

    operation_str = """
        SELECT *
            FROM organisation{0} AS o
            WHERE o.id = %s
        """.format(table_variant)

    description, results = _db_query(operation_str, (org_id,), False)

    if not len(results) == 1:
            return {}
    else:
        org = results[0]

        operation_str = """
            SELECT * from autonomous_system{0} AS a
                JOIN organisation_to_asn{0} AS oa
                    ON oa.asn_id = a.number
                WHERE oa.organisation_id = %s
            """.format(table_variant)

        description, results = _db_query(operation_str, (org_id,), False)
        org["asns"] = results

        operation_str = """
            SELECT * from contact{0} AS c
                JOIN role{0} AS r
                    ON r.contact_id = c.id
                WHERE r.organisation_id = %s
            """.format(table_variant)

        description, results = _db_query(operation_str, (org_id,), True)
        org["contacts"] = results

        return org

def _create_org(org):
    log.debug("_create_org called with " + repr(org))
    pass

def _update_org(org):
    log.debug("_update_org called with " + repr(org))
    pass

def _delete_org(org):
    log.debug("_delete_org called with " + repr(org))
    pass

@hug.startup()
def setup(api):
    config = read_configuration()
    if "logging_level" in config:
        log.setLevel(config["logging_level"])
    open_db_connection(config["libpg conninfo"])
    log.debug("Initialised DB connection for contactdb_api.")


@hug.get(ENDPOINT_PREFIX + '/ping')
def pong():
    return ["pong"]


@hug.get(ENDPOINT_PREFIX + '/searchasn')
def searchasn(asn:int):
    return __db_query_organisation_ids("""
        SELECT array_agg(oa.organisation_id) as organisation_ids
            FROM autonomous_system{0} AS a
            JOIN organisation_to_asn{0} AS oa
                ON oa.asn_id = a.number
            WHERE number=%s
            GROUP BY a
        """, (asn,))

@hug.get(ENDPOINT_PREFIX + '/searchorg')
def searchorg(name:str):
    return __db_query_organisation_ids("""
        SELECT array_agg(o.id) AS organisation_ids
            FROM organisation{0} AS o
            WHERE name=%s
            GROUP BY name
        """, (name,))

@hug.get(ENDPOINT_PREFIX + '/searchcontact')
def searchorg(email:str):
    return __db_query_organisation_ids("""
        SELECT array_agg(r.organisation_id) AS organisation_ids
            FROM role{0} AS r
            JOIN contact{0} AS c
                ON c.id = r.contact_id
            WHERE c.email=%s
            GROUP BY c.email
        """, (email,))

@hug.get(ENDPOINT_PREFIX + '/org/manual/{id}')
def get_manual_org_details(id:int):
    return __db_query_org(id,"")

@hug.get(ENDPOINT_PREFIX + '/org/auto/{id}')
def get_auto_org_details(id:int):
    return __db_query_org(id,"_automatic")

# a way to test this is similiar to
#   import requests
#   requests.post('http://localhost:8000/api/contactdb/org/manual/commit', json={'one': 'two'}, auth=('user', 'pass')).json()
@hug.post(ENDPOINT_PREFIX + '/org/manual/commit')
def commit_pending_org_changes(body, response):

    known_commands = { # list of commands and function table
        'create': _create_org,
        'update': _update_org,
        'delete': _delete_org
        }
    log.info("Got commit_object: " + repr(body))
    if not (body
            and 'commands' in body
            and len(body['commands']) > 0
            and 'orgs' in body
            and len(body['orgs']) > 0
            and len(body['commands']) == len(body['orgs'])):
        response.status = HTTP_BAD_REQUEST
        return {'reason': "Needs commands and orgs arrays of same length."}

    commands = body['commands']
    orgs =  body['orgs']

    for command in commands:
        if not command in known_commands:
            response.status = HTTP_BAD_REQUEST
            return {'reason':
                    "Unknown command. Not in " + str(known_commands.keys())}

    resultingIDs = []
    try:
        for command, org in zip(commands, orgs):
            resultingIDs.append(known_commands[command](org))
    except Exception as err:
        __rollback_transaction()
        log.exception("Commit failed '%s' with '%r'", command, org)
        response.status = HTTP_BAD_REQUEST
        return {"reason": "Commit failed, see server logs."}
    else:
        __commit_transaction()

    return resultingIDs

def main():
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

    cur = open_db_connection(config["libpg conninfo"]).cursor()

    for count in [
            "autonomous_system_automatic",
            "autonomous_system",
            "organisation_automatic",
            "organisation",
            "contact_automatic",
            "contact"
            ]:
        cur.execute("SELECT count(*) from {}".format(count))
        result = cur.fetchone()
        print("count {} = {}".format(count, result))

    cur.execute("SELECT count(*) from autonomous_system")
    cur.connection.commit() # end transaction
