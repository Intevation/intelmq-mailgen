#!/usr/bin/env python3
"""Check what has been send out with one cbticket.

Reuses the database configuration of intelmqmail.cb.

Requires hug (http://www.hug.rest/)


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
#import json

import hug

import intelmqmail.cb as cb

log = cb.log

config = None
conn = None
cur = None

@hug.startup()
def setup(api):
    global config, conn, cur
    config = cb.read_configuration()

    conn = cb.open_db_connection(config)
    cur = conn.cursor()


@hug.get()
@hug.cli()
def getEventIDsForTicket(ticket:hug.types.length(17, 18)):
    event_ids = []
    try:
        cur.execute("SELECT array_agg(events_id) as a FROM notifications "
                    "   WHERE intelmq_ticket = %s;", (ticket,))
        event_ids = cur.fetchone()["a"]
    finally:
        pass

    return event_ids


@hug.cli()
def getEvents(ids:hug.types.multiple):
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

#print(getEvents(getEventIDsForTicket('20161020-10000004')))
#print(getEventIDsForTicket('20100101-10000001'))

if __name__ == '__main__':
    setup(hug.API('cli'))
    getEventIDsForTicket.interface.cli()

    cur.close()
    conn.close()
