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
"""
import json
import os
import tempfile
import unittest

from contactdb_api import serve

class Tests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir_obj = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp_dir_obj.cleanup()


    def test_reading_config(self):
        self.conf_file_name = os.path.join(self._tmp_dir_obj.name, 'a.conf')

        test_config = {"a":"value", "b": 123}

        with open(self.conf_file_name, mode="wt") as file_object:
            json.dump(test_config, file_object)

        os.environ["CONTACTDB_SERVE_CONF_FILE"]=self.conf_file_name

        self.assertEqual = (serve.read_configuration(), test_config)

    def test_default_config(self):
        self.conf_file_name = os.path.join(self._tmp_dir_obj.name, 'a.conf')

        with open(self.conf_file_name, mode="wt") as file_object:
            file_object.write(serve.EXAMPLE_CONF_FILE)

        os.environ["CONTACTDB_SERVE_CONF_FILE"]=self.conf_file_name

        self.assertIsInstance(serve.read_configuration(), dict)
