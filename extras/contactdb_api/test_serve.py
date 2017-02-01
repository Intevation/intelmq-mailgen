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
