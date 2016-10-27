"""Prototype intelmq-mailgen checkticket web app

Using
    pip3 install git+https://github.com/dddomodossola/remi.git

start with
    python3 ${basename}
make sure that the websocket port can be accessed from the browser.

Derived from remi/examples/simple_app.py
"""
from datetime import datetime

import remi.gui as gui
from remi import start, App

import intelmqmail.cb as cb

class MyApp(App):
    def __init__(self, *args):
        super(MyApp, self).__init__(*args)

        # initialising db connection
        self.config = cb.read_configuration()
        self.conn = cb.open_db_connection(self.config, connection_factory=None)
        self.cur = self.conn.cursor()

    def _getEventIDsForTicket(self, ticket: str):
        event_ids = []
        try:
            self.cur.execute("SELECT array_agg(events_id) as a "
                             "  FROM notifications "
                             "  WHERE intelmq_ticket = %s;", (ticket,))
            event_ids = self.cur.fetchone()[0]
        finally:
            pass

        return event_ids

    def _getEvents(self, ids):
        events = []

        try:
            self.cur.execute("SELECT * FROM events WHERE id = ANY(%s)", (ids,))

            description_row = []
            for c in self.cur.description:
                description_row.append(c[0])

            rows = self.cur.fetchall()

            # try to eliminate emptry rows and raw (TODO: do it more elegant)
            #
            # description_row=['a','b','c','d']
            # rows = [ [1,None,3,None], [2,None, 4,None], [None, None, 1, None]]
            #
            # step 1: finding the filled columns
            list_of_filled_colums = []
            for i in range(len(description_row)):
                if description_row[i] == 'raw':
                    continue
                for j in range(len(rows)):
                    if rows[j][i] != None:
                        list_of_filled_colums.append(i)
                        break

            # initialize new target rows, one more for the description row
            for j in range(len(rows)+1):
                events.append([])

            #step 2: reassemble new matrix
            for i in list_of_filled_colums:
                events[0].append(description_row[i])
                for j in range(len(rows)):
                    value = rows[j][i]
                    if isinstance(value, datetime):
                        value = str(value)
                    events[j+1].append(value)

        finally:
            pass

        return events

    def main(self, name='CERT-Bund Checkticket'):
        wid = gui.VBox(width='80%')
        lbl = gui.Label('%s' % name, width='80%', height='50%')
        lbl.style['margin'] = 'auto'

        self.txt = gui.TextInput(width=200, height=30, margin='10px')
        self.txt.set_text('20161020-10000004')
        self.txt.set_on_change_listener(self.on_text_area_change)

        self.ids = []

        idcontainer =  gui.Widget(
            width='80%',
            layout_orientation=gui.Widget.LAYOUT_HORIZONTAL,
            margin='5px')

        self.idLabel =  gui.Label('Event IDs: ')
        self.idList = gui.Label('')

        idcontainer.append(self.idLabel)
        idcontainer.append(self.idList)

        self.output = gui.Label('')
        self.table = gui.Table()

        wid.append(lbl)
        wid.append(self.txt)
        wid.append(idcontainer)
        wid.append(self.table)
        wid.append(self.output)

        # returning the root widget
        return wid

    def on_text_area_change(self, widget, newValue):
        self.ids = self._getEventIDsForTicket(newValue)
        self.idList.set_text(str(self.ids))

        if self.ids != None and len(self.ids) > 0:
            events = self._getEvents(self.ids)

            self.table.from_2d_matrix(events)

            self.output.set_text("Raw output:" + str(events))

if __name__ == "__main__":
    print("hi")
    start(MyApp, debug=True, start_browser=False, websocket_port=40000)
