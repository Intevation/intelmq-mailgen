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

import hug
import logging

# Logging
logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # using INFO as default, otherwise it's WARNING

ENDPOINTS = {}

# if possible add the contactdb_api to our endpoints
try:
    import contactdb_api.serve

    @hug.extend_api()
    def add_contactdb_api():
        return[contactdb_api.serve]

    ENDPOINTS[contactdb_api.serve.ENDPOINT_NAME] = contactdb_api.serve.ENDPOINT_PREFIX

except ImportError as err:
    log.warning(err)

# if possible add the eventdb_api to our endpoints
try:
    import events_api.serve

    @hug.extend_api()
    def add_events_api():
        return[events_api.serve]

    ENDPOINTS[events_api.serve.ENDPOINT_NAME] = events_api.serve.ENDPOINT_PREFIX

except ImportError as err:
    log.warning(err)


# if possible add the checkticket_api to our endpoints
try:
    import checkticket_api.serve

    @hug.extend_api()
    def add_checkticket_api():
        return[checkticket_api.serve]

    ENDPOINTS[checkticket_api.serve.ENDPOINT_NAME] = checkticket_api.serve.ENDPOINT_PREFIX

except ImportError as err:
    log.warning(err)

@hug.startup()
def setup(api):
    pass

@hug.get("/")
def get_endpoints():
    return ENDPOINTS


if __name__ == '__main__':
    # expose only one function to the cli
    setup(hug.API('cli'))
    get_endpoints()
