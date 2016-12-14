#!/usr/bin/env python3
"""Check what has been send out with one cbticket.

Reuses the database configuration of intelmqmail.cb.

Requires hug (http://www.hug.rest/)

Development: call like
  hug -f checkticket.py
  connect to http://localhost:8000/

Several configuration methods are shown within the code.


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
# the intelmqmail module needs an UTF-8 locale, so we set a common one
# available in Ubuntu 14.04/LTS here explicitely. This also removes the
# necessity configure calling http server to set the locale correctly.
import os
os.environ['LANG']= 'en_US.UTF-8'

from psycopg2.extras import DictConnection
import hug

import intelmqmail.cb as cb
import intelmqmail.db as db

log = cb.log

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

###
## when called from a web application that has been served from
## a different port, we can allow the browser to read from us
##
##
## uncomment (== activate) the following lines:
#allow_8080_header = {
#            "Access-Control-Allow-Origin" : "http://localhost:8080"
#            }
#
## for each allowed endpoint then add it to the response_headers, 
## e.g. replace each @hug.get() with 
#@hug.get(response_headers = allow_8080_header)


@hug.cli()
@hug.get()
def getEventIDsForTicket(ticket:hug.types.length(17, 18)):
    global cur
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
        pass

    return events

@hug.get()
def getEventsForTicket(ticket:hug.types.length(17, 18)):
    return getEvents(getEventIDsForTicket(ticket))


@hug.get()
def getLastTicketNumber():
    global cur
    return db.last_ticket_number(cur)

###
## When serving a single page web application in a more complex setup,
## we may serve a main html page for root ('/') and static
## files from a directory.
##
## adapt and uncomment (== activate) the following lines:
#@hug.get('/', output=hug.output_format.file)
#def root():
#        return("/home/fody/www/index.html")
#
#@hug.static('/static')
#def my_static_dirs():
#        return("/home/fody/www/static",)
###

###
## serving the static files for the single page web application
## (in a simple manner)
##
## uncomment (== activate) the following lines:
#
#@hug.get('/index.html', output=hug.output_format.file)
#def index():
#    return("./checkticket.html")
#
#@hug.get('/vue.js', output=hug.output_format.file)
#def vue():
#    return("./vue.js")
#
#@hug.get('/vue-resource.min.js', output=hug.output_format.file)
#def vue_resource():
#    return("./vue-resource.min.js")
#
#@hug.get('/jquery.min.js', output=hug.output_format.file)
#def jquery():
#    return("./jquery-3.1.1.min.js")
#
#@hug.get('/semantic.min.js', output=hug.output_format.file)
#def semantic_js():
#    return("./semantic.min.js")
#
#@hug.get('/semantic.min.css', output=hug.output_format.file)
#def semantic_css():
#    return("./semantic.min.css")
#
###

###
## test lines to see if the access to the db works, use valid parameters
#print(getEvents(getEventIDsForTicket('20161020-10000004')))
#print(getEventIDsForTicket('20100101-10000001'))
###

if __name__ == '__main__':
    # expose only one function to the cli
    setup(hug.API('cli'))
    getEventIDsForTicket.interface.cli()

    cur.close()
    conn.close()
