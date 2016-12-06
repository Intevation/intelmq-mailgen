#!/usr/bin/env python3
"""Check what has been send out with one cbticket.

Reuses the database configuration of intelmqmail.cb.

Requires hug (http://www.hug.rest/)

Development: call like
  hug -f checkticket.py
  connect to http://localhost:8000/


Copyright (C) 2016 by Bundesamt für Sicherheit in der Informationstechnik
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
"""
from psycopg2.extras import DictConnection
import hug

import intelmqmail.cb as cb
import intelmqmail.db as db

log = cb.log

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
@hug.get()
def getEventIDsForTicket(ticket:hug.types.length(17, 18)):
    event_ids = []
    try:
        cur.execute("SELECT array_agg(events_id) as a FROM notifications "
                    "   WHERE intelmq_ticket = %s;", (ticket,))
        event_ids = cur.fetchone()["a"]
    finally:
        pass

    return event_ids

class ListOfIds(hug.types.Multiple):
    """Only accept a list of numbers."""

    def __call__(self, value):
        value = super().__call__(value)
        return [int(i) for i in value]


@hug.cli()
@hug.get()
def getEvents(ids:ListOfIds()):
    events = []

    try:
        cur.execute("SELECT * FROM events WHERE id = ANY(%s)", (ids,))
        rows = cur.fetchall()
        for row in rows:
            # remove None entries from the resulting dict
            event = {k:v for k,v in row.items() if v != None}
            events.append(event)
    finally:
        pass

    return events

allow_8080_header = {
            "Access-Control-Allow-Origin" : "http://localhost:8080"
            }

@hug.get(response_headers = allow_8080_header)
def getLastTicketNumber():
    return db.last_ticket_number(cur)

#
# serving the static files for the single page web application
# (in a simple manner)
#

@hug.get('/index.html', output=hug.output_format.file)
def index():
    return("./checkticket.html")

@hug.get('/vue.js', output=hug.output_format.file)
def vue():
    return("./vue.js")

@hug.get('/vue-resource.min.js', output=hug.output_format.file)
def vue_resource():
    return("./vue-resource.min.js")

@hug.get('/jquery.min.js', output=hug.output_format.file)
def jquery():
    return("./jquery-3.1.1.min.js")

@hug.get('/semantic.min.js', output=hug.output_format.file)
def semantic_js():
    return("./semantic.min.js")

@hug.get('/semantic.min.css', output=hug.output_format.file)
def semantic_css():
    return("./semantic.min.css")


#print(getEvents(getEventIDsForTicket('20161020-10000004')))
#print(getEventIDsForTicket('20100101-10000001'))

if __name__ == '__main__':
    setup(hug.API('cli'))
    getEventIDsForTicket.interface.cli()

    cur.close()
    conn.close()
