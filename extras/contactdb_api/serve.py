#!/usr/bin/env python3
"""Serve intelmq-certbund-contact db api via wsgi.

Requires hug (http://www.hug.rest/)


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


Design rationale:
    Our services shall be accessed by https://github.com/Intevation/intelmq-fody
    so our "endpoints" should be reachable from the same ip:port as
    the checkticket endpoints.

    We need location and credentials for the database holding the contactdb.
    checkticket.py [1] (a hug based backend) solves this problem by reusing
    the intelmq-mailgen configuration to access the 'intelmq-events' database.
    This serving part need to access a different database 'contactdb', thus
    we start with our on configuration.

    [1] https://github.com/Intevation/intelmq-mailgen/blob/master/extras/checkticket-spa/checkticket.py

"""
import json
import logging
import os
import sys

import psycopg2
from psycopg2.extras import DictConnection


#import hug

log = logging.getLogger(__name__)

def read_configuration() -> dict:
    """Read configuration file.

    If the environment variable CONTACTDB_SERVE_CONF_FILE exist, use it
    for the file name. Otherwise uses a default.

    Returns:
        The configuration values, possibly containing more dicts.

    Notes:
      Design rationale
      ----------------
        * Okay separation from config and code.
        * Better than intelmq-mailgen which has two hard-coded places 
          and merge code.
        * (Inspired by https://12factor.net/config.)
    """
    config = None
    config_file_name = os.environ.get(
                        "CONTACTDB_SERVE_CONF_FILE",
                        "/etc/intelmq/contactdb-serve.conf")

    if os.path.isfile(config_file_name):
        with open(config_file_name) as config_handle:
                config = json.load(config_handle)

    return config if isinstance(config, dict) else {}

EXAMPLE_CONF_FILE = r"""
{ "libpg conninfo":
    "host=localhost dbname=contactdb user=intelmq password='USER\\'s DB PASSWORD'"
}
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--example-conf':
        print(EXAMPLE_CONF_FILE)
        exit()

    config = read_configuration()
    print("config = {}".format(config,))

    con = psycopg2.connect(dsn=config["libpg conninfo"],
                           connection_factory=DictConnection)
    cur = con.cursor()

    for count in [
            "autonomous_system_automatic",
            "autonomous_system",
            "organisation_automatic",
            "organisation",
            "contact_automatic",
            "contact"
            ]:
        cur.execute("SELECT count(*) from {}".format(count))
        result = cur.fetchone()
        print("count {} = {}".format(count, result))

    cur.execute("SELECT count(*) from autonomous_system")
