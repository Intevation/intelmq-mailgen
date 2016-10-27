"""Prototype intelmq-mailgen checkticket web app

Using
    pip3 install git+https://github.com/dddomodossola/remi.git

start with
    python3 ${basename}
make sure that the websocket port can be accessed from the browser.

Derived from remi/examples/simple_app.py
"""

import remi.gui as gui
from remi import start, App

import checkticket

class MyApp(App):
    def __init__(self, *args):
        print("ho")
        super(MyApp, self).__init__(*args)

    def main(self, name='CERT-Bund Checkticket'):
        wid = gui.VBox(width=300, height=200)
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

        wid.append(lbl)
        wid.append(self.txt)
        wid.append(idcontainer)

        checkticket.setup(checkticket.hug.API('local'))

        # returning the root widget
        return wid

    def on_text_area_change(self, widget, newValue):
        self.ids = checkticket.getEventIDsForTicket(newValue)
        self.idList.set_text(str(self.ids))


if __name__ == "__main__":
    print("hi")
    start(MyApp, debug=True, start_browser=False, websocket_port=40000)
