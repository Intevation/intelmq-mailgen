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

from falcon import HTTP_BAD_REQUEST, HTTP_NOT_FOUND
import hug
import psycopg2
from psycopg2.extras import RealDictCursor



log = logging.getLogger(__name__)
# adding a custom log level for even more details when diagnosing
DD = logging.DEBUG-2
logging.addLevelName(DD, "DDEBUG")

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

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class CommitError(Error):
    """Exception raises if a commit action fails.
    """
    pass

# Using a global object for the database connection
# must be initialised once
contactdb_conn = None

def open_db_connection(dsn:str):
    global contactdb_conn

    contactdb_conn = psycopg2.connect(dsn=dsn)
    return contactdb_conn

def __commit_transaction():
    global contactdb_conn
    log.log(DD, "Calling commit()")
    contactdb_conn.commit()

def __rollback_transaction():
    global contactdb_conn
    log.log(DD, "Calling rollback()")
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
    log.log(DD, "Ran query '{}'".format(str(cur.query)))
    description = cur.description
    results = cur.fetchall()

    if end_transaction:
        __commit_transaction()

    cur.close()

    return (description, results)

def _db_manipulate(operation:str, parameters=None,
                   end_transaction:bool=True) -> int:
    """Manipulates the database.

    Creates a cursor from the global database connection, runs the command.

    Parameters:
        operation: The query to be used by psycopg2.cursor.execute()
        parameters: for the sql query
        end_transaction: set to False to do subsequent queries in the same
            transaction.

    Returns:
        Number of affected rows.
    """
    global contactdb_conn

    # pscopgy2.4 does not offer 'with' for cursor()
    # FUTURE use with
    cur = contactdb_conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(operation, parameters)
    log.log(DD, "Ran query '{}'".format(str(cur.query)))
    if end_transaction:
        __commit_transaction()
    cur.close()

    return cur.rowcount

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


def __db_query_org(org_id:int, table_variant:str,
                   end_transaction:bool=True) -> dict:
    """Returns details for an organisaion.

    Parameters:
        org_id:int: the organisation id to be queries
        table_variant: either "" or "_automatic"

    Returns:
        containing the organisation and additional keys
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

        description, results = _db_query(operation_str, (org_id,),
                                         end_transaction)
        org["contacts"] = results

        return org

def __db_query_asn(asn:int, table_variant:str,
                   end_transaction:bool=True) -> dict:
    """Returns details for an asn."""

    operation_str = """
                SELECT * from autonomous_system{0} as a
                    WHERE number = %s
                """.format(table_variant)
    description, results = _db_query(operation_str, (asn,), end_transaction)

    if len(results) > 0:
        return results[0]
    else:
        return None


def __check_or_create_asns(asns:list) -> list:
    """Find or creates db entries for asns.

    Parameter:
        asns: asns to be found or created

    Returns:
        List of tuples with asn_id and notification intervall.
    """
    new_numbers = []
    for asn in asns:
        if "ripe_aut_num" in asn and asn["ripe_aut_num"] != None:
            raise CommitError("ripe_aut_num is set")

        if asn["comment"] == None:
            raise CommitError("comment is not set")

        asn_in_db = __db_query_asn(asn["number"], "", False)

        if asn_in_db != None:
            operation_str = """
                SELECT a.number FROM autonomous_system AS a
                    WHERE a.number = %(number)s AND a.comment = %(comment)s
                """
            description, results = _db_query(operation_str, asn, False)

            if len(results) == 1:
                new_numbers.append((results[0]["number"],
                                    asn['notification_interval']))
            else:
                raise CommitError("The ASN{} already exists"
                                  " with other comment.".format(asn["number"]))
        else:
            operation_str = """
                INSERT INTO autonomous_system
                    (number, comment)
                    VALUES (%(number)s, %(comment)s)
                """
            affected_rows = _db_manipulate(operation_str, asn, False)
            new_numbers.append((asn["number"], asn['notification_interval']))

    return new_numbers

def __remove_or_unlink_asns(asns:list, org_id:int) -> None:
    """Removes or unlinks db entries for asns.

    Parameter:
        asns: to be unlinked or removed
        org_id: the organisation to be unlinked from
    """
    for asn in asns:
        asn_id = asn["number"]
        operation_str = """
            DELETE FROM organisation_to_asn AS oa
                WHERE oa.organisation_id = %s
                  AND oa.asn_id = %s
            """
        _db_manipulate(operation_str, (org_id, asn_id), False)

        #how many connections are left to this asn?
        operation_str = """
            SELECT count(*) FROM organisation_to_asn WHERE asn_id = %s
            """
        description, results = _db_query(operation_str, (asn_id,) , False)

        if results[0]["count"] == 0:
            # delete asn, because there is no connection anymore

            asn_in_db = __db_query_asn(asn_id, "", False)

            # ignore in the comparison, because it comes from the n-to-m table
            del(asn["notification_interval"])
            del(asn["organisation_id"])
            del(asn["asn_id"])
            if asn_in_db == asn:
                operation_str = """
                    DELETE FROM autonomous_system
                      WHERE number = %s
                    """
                _db_manipulate(operation_str, (asn_id,), False)
            else:
                log.debug("asn_in_db = {}; asn = {}".format(
                            repr(asn_in_db), repr(asn)))
                raise CommitError("ASN{} to be deleted differs from db entry."
                                  "".format(asn_id))

def __check_or_update_asns(asns:list, org_id:int) -> None:
    """Checks or updates and links as necessary asns for an org.

    For each asn:
        Reuse and update
        or create

    Parameter:
        asns: to be worked on
        org_id: the org to link to
    """

    for asn in asns:
        asn_id = asn["number"]

        # do we already have an asn that has the necessary values?
        asn_in_db = __db_query_asn(asn_id, "", False)

        if asn_in_db == None:
            # create
            # TODO join with creation in __check_or_create_asns()
            operation_str = """
                INSERT INTO autonomous_system
                    (number, comment) VALUES (%(number)s, %(comment)s)
                """
            _db_manipulate(operation_str, asn, False)
        elif asn_in_db["comment"] != asn["comment"]:
            # update comment (the only field changeable)
            operation_str = """
                UPDATE autonomous_system
                    SET comment = %(comment)s
                    WHERE number = %(number)s
                """
            _db_manipulate(operation_str, asn, False)

        # check the linking
        operation_str = """
            SELECT * FROM organisation_to_asn
                WHERE organisation_id = %s
                  AND asn_id = %s
            """
        description, results = _db_query(operation_str,
                                        (org_id, asn_id,), False)
        if len(results) == 0:
            # add link
            operation_str = """
                INSERT INTO organisation_to_asn
                    (organisation_id, asn_id, notification_interval)
                    VALUES (%s, %s, %s)
                """
            _db_manipulate(operation_str, (org_id, asn_id,
                                           asn['notification_interval']), False)
    ## TODO remove superfluous links
    #operation_str = """
    #    DELETE FROM organisation_to_asn
    #        WHERE number != ALL(%s)
    #    """
    # use array



def __remove_or_unlink_contacts(contacts:list, org_id:int) -> None:
    """Removes or unlinks db entries for contacts.

    Parameter:
        contacts: to be unlinked or removed
        org_id: the organisation to be unlinked from
    """
    for contact in contacts:
        contact_id = contact["contact_id"]
        operation_str = """
            DELETE from role
                WHERE organisation_id = %s
                  AND contact_id = %s
            """
        _db_manipulate(operation_str, (org_id, contact_id), False)

        # how many connection are left to this contact?
        operation_str = """SELECT count(*) FROM role WHERE contact_id = %s"""
        description, results = _db_query(operation_str, (contact_id,) , False)

        if results[0]["count"] == 0:
            # delete contact, because there is no connection anymore

            operation_str = "DELETE from contact WHERE id = %s"
            _db_manipulate(operation_str, (contact_id,), False)


def __check_or_create_contacts(contacts:list) -> list:
    new_contact_ids = []

    needed_attribs = ['firstname', 'lastname', 'tel', 'openpgp_fpr',
                     'email', 'format_id', 'comment']

    for contact in contacts:
        # we need make sure that all values are there and at least ''
        # as None would be translated to '= NULL' which always fails in SQL
        for attrib in needed_attribs:
            if (not attrib in contact) or contact[attrib] == None:
                raise CommitError("{} not set".format(attrib))
        operation_str = """
            SELECT c.id FROM contact AS c
                WHERE c.firstname = %(firstname)s
                  AND c.lastname = %(lastname)s
                  AND c.tel = %(tel)s
                  AND c.openpgp_fpr = %(openpgp_fpr)s
                  AND c.email = %(email)s
                  AND c.format_id = %(format_id)s
                  AND c.comment = %(comment)s
            """
        description, results = _db_query(operation_str, contact, False)

        if len(results) > 1:
            raise CommitError("More than one contact "
                              "with {} in the db".format(contact))
        elif len(results) == 1:
            new_contact_ids.append(results[0]["id"])
        else:
            operation_str = """
                INSERT INTO contact
                    (firstname, lastname, tel,
                     openpgp_fpr, email, format_id, comment)
                    VALUES (%(firstname)s, %(lastname)s, %(tel)s,
                            %(openpgp_fpr)s, %(email)s, %(format_id)s,
                            %(comment)s)
                    RETURNING id
                """
            description, results = _db_query(operation_str, contact, False)
            new_contact_ids.append(results[0]["id"])

    return new_contact_ids

def __check_or_update_contacts(contacts:list, org_id:int):
    """Create or update and then link contact if necessary.
    """

    #TODO refactor with __check_or_create_contacts()

    needed_attribs = ['firstname', 'lastname', 'tel', 'openpgp_fpr',
                      'email', 'format_id', 'comment']

    for contact in contacts:
        # sanity check
        for attrib in needed_attribs:
            if (not attrib in contact) or contact[attrib] == None:
                raise CommitError("Updating Org {} contacts: "
                                  "{} not set".format(org_id, attrib))

        operation_str = """
            SELECT c.id FROM contact AS c
                WHERE c.firstname = %(firstname)s
                  AND c.lastname = %(lastname)s
                  AND c.tel = %(tel)s
                  AND c.openpgp_fpr = %(openpgp_fpr)s
                  AND c.email = %(email)s
                  AND c.format_id = %(format_id)s
                  AND c.comment = %(comment)s
            """
        description, results = _db_query(operation_str, contact, False)

        if len(results) >= 1:
            # use the first found
            new_contact_id = results[0]["id"]
        elif id in contact:
            # update
            operation_str = """
                UPDATE contact
                    SET (firstname, lastname, tel,
                         openpgp_fpr, email, format_id, comment)
                      = (%(firstname)s, %(lastname)s, %(tel)s,
                         %(openpgp_fpr)s, %(email)s, %(format_id)s,
                         %(comment)s)
                    WHERE id = %(id)s
                """
            _db_manipulate(operation_str, contact, False)
            new_contact_id = contact["id"]
        else:
            #create
            # TODO refactor with __check_or_create_contacts()
            operation_str = """
                INSERT INTO contact
                    (firstname, lastname, tel,
                     openpgp_fpr, email, format_id, comment)
                    VALUES (%(firstname)s, %(lastname)s, %(tel)s,
                            %(openpgp_fpr)s, %(email)s, %(format_id)s,
                            %(comment)s)
                    RETURNING id
                """
            description, results = _db_query(operation_str, contact, False)
            new_contact_id = results[0]["id"]

        # fix the linking
        operation_str = """
            SELECT * FROM role
                WHERE organisation_id = %s
                  AND contact_id = %s
            """
        description, results = _db_query(operation_str,
                                         (org_id, new_contact_id), False)

        if len(results) == 0:
            # add link
            operation_str = """
                INSERT INTO role
                    (organisation_id, contact_id)
                    VALUES (%s, %s)
                """
            _db_manipulate(operation_str, (org_id, new_contact_id), False)

    # TODO remove superfluous links


def _create_org(org:dict) -> int:
    """Insert an new contactdb entry.

    Makes sure that the contactdb entry expressed by the org dict
    is in the tables for manual entries.

    First checks the linked asns and linked contact tables.
    Then checks the organisation itself.
    Afterwards checks the n-to-m entries that link the tables.

    By each check queries if an entry with equal values is already in the table.
    If so, uses the existing entry, otherwise inserts a new entry.

    Returns:
        Database ID of the organisation that has been there or was created.
    """
    log.debug("_create_org called with " + repr(org))

    new_asn_ids = __check_or_create_asns(org['asns'])
    log.debug("new_asn_ids = " + repr(new_asn_ids))
    new_contact_ids = __check_or_create_contacts(org['contacts'])
    log.debug("new_contact_ids = " + repr(new_contact_ids))

    needed_attribs = ['name', 'comment', 'ripe_org_hdl',
                      'ti_handle', 'first_handle']

    for attrib in needed_attribs:
        if attrib in org:
            if org[attrib] == None:
                org[attrib] == ''
        else:
            raise CommitError("{} not set".format(attrib))

    operation_str = """
        SELECT o.id FROM organisation as o
            WHERE o.name = %(name)s
              AND o.comment = %(comment)s
              AND o.ripe_org_hdl = %(ripe_org_hdl)s
              AND o.ti_handle = %(ti_handle)s
              AND o.first_handle = %(first_handle)s
        """
    if (('sector_id' not in org) or org['sector_id'] == None
            or org['sector_id'] == ''):
        operation_str += " AND o.sector_id IS NULL"
        org["sector_id"] = None
    else:
        operation_str += " AND o.sector_id = %(sector_id)s"

    description, results = _db_query(operation_str, org, False)
    if len(results) > 1:
        raise CommitError("More than one organisation row like"
                          " {} in the db".format(org))
    elif len(results) == 1:
        new_org_id = results[0]["id"]
    else:
        operation_str = """
            INSERT INTO organisation
                (name, sector_id, comment, ripe_org_hdl,
                 ti_handle, first_handle)
                VALUES (%(name)s, %(sector_id)s, %(comment)s, %(ripe_org_hdl)s,
                        %(ti_handle)s, %(first_handle)s)
                RETURNING id
            """
        description, results = _db_query(operation_str, org, False)
        new_org_id = results[0]["id"]

    for asn, notification_interval in new_asn_ids:
        operation_str = """
            SELECT * FROM organisation_to_asn
                WHERE organisation_id = %s
                  AND asn_id = %s
                  AND notification_interval = %s
            """
        description, results = _db_query(
            operation_str, (new_org_id, asn, notification_interval), False
            )
        if len(results) < 1:

            operation_str = """
                INSERT INTO organisation_to_asn
                    (organisation_id, asn_id, notification_interval)
                    VALUES ( %s, %s, %s )
                """
            affected_rows = _db_manipulate(
                operation_str, (new_org_id, asn, notification_interval),
                False
                )

    for contact_id in new_contact_ids:
        operation_str = """
            SELECT * FROM role
                WHERE organisation_id = %s
                  AND contact_id = %s
            """
        description, results = _db_query(operation_str,
                                         (new_org_id, contact_id), False)
        if len(results) < 1:
            operation_str = """
                INSERT INTO role
                    (organisation_id, contact_id)
                    VALUES ( %s, %s )
                """
            affected_rows = _db_manipulate(operation_str,
                                           (new_org_id, contact_id), False)

    return(new_org_id)


def _update_org(org):
    """Update a contactdb entry.

    Returns:
        Database ID of the updated organisation.
    """
    log.debug("_update_org called with " + repr(org))

    org_id = org["id"]
    org_in_db = __db_query_org(org_id, "", end_transaction=False)

    if ("id" not in org_in_db) or org_in_db["id"] != org_id:
        raise CommitError("Org {} to be updated not in db.".format(org_id))

    __check_or_update_asns(org["asns"], org_id)
    __check_or_update_contacts(org["contacts"], org_id)

    # linking of asns and contacts has been done, only update is left to do
    operation_str = """
        UPDATE organisation
            SET (name, sector_id, comment, ripe_org_hdl,
                 ti_handle, first_handle)
              = (%(name)s, %(sector_id)s, %(comment)s, %(ripe_org_hdl)s,
                 %(ti_handle)s, %(first_handle)s)
            WHERE id = %(id)s
        """
    _db_manipulate(operation_str, org, False)

    return org_id


def _delete_org(org) -> int:
    """Delete an contactdb entry.

    Also delete the attached asns and contact entries, if they are
    not used elsewhere.

    Returns:
        Database ID of the organisation that has been deleted.
    """
    log.debug("_delete_org called with " + repr(org))

    org_in_db = __db_query_org(org["id"], "", end_transaction=False)

    if not org_in_db == org:
        log.debug("org_in_db = {}; org = {}".format(repr(org_in_db), repr(org)))
        raise CommitError("Org to be deleted differs from db entry.")

    __remove_or_unlink_asns(org['asns'], org['id'])
    __remove_or_unlink_contacts(org['contacts'], org['id'])

    # remove org itself
    operation_str = "DELETE FROM organisation WHERE id = %s"
    affected_rows = _db_manipulate(operation_str, (org["id"],), False)

    if affected_rows == 1:
        return org["id"]


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
def searchcontact(email:str):
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

@hug.get(ENDPOINT_PREFIX + '/asn/manual/{number}')
def get_manual_asn_details(number:int, response):
    asn = __db_query_asn(number, "")

    if asn == None:
        response.status = HTTP_NOT_FOUND
        return {"reason": "ASN not found"}
    else:
        return asn

# a way to test this is similiar to
#   import requests
#   requests.post('http://localhost:8000/api/contactdb/org/manual/commit', json={'one': 'two'}, auth=('user', 'pass')).json()
@hug.post(ENDPOINT_PREFIX + '/org/manual/commit')
def commit_pending_org_changes(body, response):

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

    known_commands = { # list of commands and function table
        'create': _create_org,
        'update': _update_org,
        'delete': _delete_org
        }

    for command in commands:
        if not command in known_commands:
            response.status = HTTP_BAD_REQUEST
            return {'reason':
                    "Unknown command. Not in " + str(known_commands.keys())}

    results = []
    try:
        for command, org in zip(commands, orgs):
            results.append((command, known_commands[command](org)))
    except Exception as err:
        __rollback_transaction()
        log.exception("Commit failed '%s' with '%r'", command, org)
        response.status = HTTP_BAD_REQUEST
        return {"reason": "Commit failed, see server logs."}
    else:
        __commit_transaction()

    log.debug("Commit successful, results = {}".format(results,))
    return results

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
