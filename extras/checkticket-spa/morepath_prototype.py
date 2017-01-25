"""Prototype to serve the checkticket-spa with morepath.

Using
    morepath v0.17 (https://morepath.readthedocs.io/en/latest/).

Development: call like
    python3 morepath_prototype.py


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
"""
from datetime import datetime

from psycopg2.extras import DictConnection
import morepath

import intelmqmail.cb as cb
import intelmqmail.db as db

class App(morepath.App):
    pass

class DBConnection():
    """Base class to keep the DB connection as class attribute.

    Will initialise the connection on first instanciation.
    TODO: There is probably a better way to do this with morepath.
    """
    conn = None
    cur = None

    def __init__(self):
        if DBConnection.conn == None:
            # initialising db connection
            config = cb.read_configuration()
            DBConnection.conn = cb.open_db_connection(
                                    config, connection_factory=DictConnection)

        if DBConnection.cur == None:
            # get a new cursor, if we don't have one
            DBConnection.cur = DBConnection.conn.cursor()


@App.path(path='')
class Root(object):
        pass


class EventIDs(DBConnection):
    """Holds a list of ids for a ticket, which are queried at initialisation."""
    def __init__(self, ticket):
        super().__init__()

        self.ticket = ticket
        self.ids = []

        try:
            DBConnection.cur.execute("SELECT array_agg(events_id) as a "
                                     "  FROM notifications "
                                     "  WHERE intelmq_ticket = %s;", (ticket,))
            self.ids = DBConnection.cur.fetchone()[0]
        finally:
            pass


@App.path(model=EventIDs, path='/getEventIDsForTicket', required=['ticket'])
# TODO: use a morepath converter to check the url parameter in more detail
def get_eventids(ticket=""):
    return EventIDs(ticket)

@App.json(model=EventIDs)
def events_ids_info(self, request):

    # the request.after declarator adds a callback to manipulate the response
    # only necessary if requests come from a different server:port as the app
    @request.after
    def manipulate_response(response):
        response.headers.add("Access-Control-Allow-Origin",
                             "http://localhost:8000")

    return self.ids

class Events(DBConnection):
    def __init__(self, ticket):
        super().__init__()

        self.ticket = ticket
        self.ids = EventIDs(ticket).ids
        self.events = []

        try:
            DBConnection.cur.execute(
                    "SELECT * FROM events WHERE id = ANY(%s)", (self.ids,))

            rows = DBConnection.cur.fetchall()
            for row in rows:
                # Remove None entries from the resulting dict.
                # And transform datetime objects to string, because
                # webob calls plain json_dumps which cannot serialize datetimes.
                event = {k: (v.isoformat() if isinstance(v, datetime) else v)
                         for k,v in row.items()
                         if v != None
                        }
                self.events.append(event)
        finally:
            pass

@App.path(model=Events, path='getEventsForTicket', required=['ticket'])
def get_events(ticket=""):
        return Events(ticket)

@App.json(model=Events)
def events_info(self, request):
    @request.after
    def manipulate_response(response):
        response.headers.add("Access-Control-Allow-Origin",
                             "http://localhost:8000")
    return self.events


class LastTicket(DBConnection):
    def __init__(self):
        super().__init__()
        self.ticket = db.last_ticket_number(DBConnection.cur)

@App.path(model=LastTicket, path='getLastTicketNumber')
def get_last_ticket_number():
        return LastTicket()

@App.json(model=LastTicket)
def events_info(self, request):
    @request.after
    def manipulate_response(response):
        response.headers.add("Access-Control-Allow-Origin",
                             "http://localhost:8000")
    return self.ticket

if __name__ == '__main__':
    morepath.run(App())

