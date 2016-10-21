#!/usr/bin/env python3
"""Check what has been send out with one cbticket.

Reuses the database configuration of intelmqmail.cb.

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

import intelmqmail.cb as cb

log = cb.log

#TODO place within proper functions
config = cb.read_configuration()

cur = None
conn = cb.open_db_connection(config)

def getEventIDsForTicket(ticket = None):
    try:
        cur = conn.cursor()
        cur.execute("SELECT array_agg(events_id) as a FROM notifications "
                    "   WHERE intelmq_ticket = %s;", (ticket,))
        event_ids = cur.fetchone()["a"]
    finally:
        cur.close()

    return event_ids

#TODO def getEvents(ids):

print(getEventIDsForTicket('20161020-10000004'))
print(getEventIDsForTicket('20100101-10000001'))


#TODO place within proper function
conn.close()

