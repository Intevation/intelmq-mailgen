#!/usr/bin/env python3
"""Check what has been send out with one cbticket.

Reuses the database configuration of intelmqmail.cb.

Requires hug (http://www.hug.rest/)

Development: call like
  hug -f serve.py
  connect to http://localhost:8000/

Several configuration methods are shown within the code.


Copyright (C) 2016, 2017 by Bundesamt für Sicherheit in der Informationstechnik

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
    * Dustin Demuth <dustin@intevation.de>
"""

# The intelmqmail module needs an UTF-8 locale, so we set a common one
# available in Ubuntu 14.04/LTS here explicitely. This also removes the
# necessity to configure the calling http server to set the locale correctly.
import os
os.environ['LANG']= 'en_US.UTF-8'

from psycopg2.extras import DictConnection
import hug
import logging

log = logging.getLogger(__name__)
# adding a custom log level for even more details when diagnosing
DD = logging.DEBUG-2
logging.addLevelName(DD, "DDEBUG")


try:
    import intelmqmail.cb as cb
    import intelmqmail.db as db
except ImportError as err:
    log.error(err)

ENDPOINT_PREFIX = '/api/checkticket'
ENDPOINT_NAME = 'Checkticket'

# We are using global variables for postgresql db connection
# TODO: should be checked that parallel requests via hug/falcon behave well
# TODO: a cleanup and reopening may be better if we run this long time
config = None
conn = None
cur = None

@hug.startup()
def setup(api):
    global config, conn, cur
    config = cb.read_configuration()

    conn = cb.open_db_connection(config, connection_factory=DictConnection)
    cur = conn.cursor()


@hug.cli()
@hug.get(ENDPOINT_PREFIX  + '/getEventIDsForTicket')
def getEventIDsForTicket(ticket:hug.types.length(17, 18)):
    global cur
    event_ids = []
    try:
        cur.execute("SELECT array_agg(d.events_id) AS a FROM directives AS d "
                    "   JOIN sent ON d.sent_id = sent.id "
                    "   WHERE sent.intelmq_ticket = %s;", (ticket,))
        event_ids = cur.fetchone()["a"]
    finally:
        cur.connection.commit() # end transaction

    return event_ids

class ListOfIds(hug.types.Multiple):
    """Only accept a list of numbers."""

    def __call__(self, value):
        value = super().__call__(value)
        return [int(i) for i in value]


@hug.cli()
@hug.get(ENDPOINT_PREFIX  + '/getEvents')
def getEvents(ids:ListOfIds()):
    global cur
    events = []

    try:
        cur.execute("SELECT * FROM events WHERE id = ANY(%s)", (ids,))
        rows = cur.fetchall()
        for row in rows:
            # remove None entries from the resulting dict
            event = {k:v for k,v in row.items() if v != None}
            events.append(event)
    finally:
        cur.connection.commit() # end transaction

    return events

@hug.get(ENDPOINT_PREFIX + '/getEventsForTicket')
def getEventsForTicket(ticket:hug.types.length(17, 18)):
    return getEvents(getEventIDsForTicket(ticket))


@hug.get(ENDPOINT_PREFIX + '/getLastTicketNumber')
def getLastTicketNumber():
    global cur
    last_ticket_number = None
    try:
        last_ticket_number = db.last_ticket_number(cur)
    finally:
        cur.connection.commit() # end transaction

    return last_ticket_number

def main():
    # expose only one function to the cli
    setup(hug.API('cli'))
    getEventIDsForTicket.interface.cli()

    cur.close()
    conn.close()
