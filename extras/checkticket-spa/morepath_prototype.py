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

import morepath

class App(morepath.App):
    pass

class EventIDs(Object):
    def __init__(self, ticket):
        self.ids = []
        self.ticket = ticket

@App.path(model=EventIDs, path='/getEventIDsForTicket')
#TODO

if __name__ == '__main__':
    morepath.run(App())

